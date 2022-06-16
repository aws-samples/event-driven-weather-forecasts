#!/bin/bash -l

. /etc/parallelcluster/cfnconfig
. /etc/profile.d/spack.sh

test "$cfn_node_type" != "HeadNode" && exit

set -eux

main() {
  local region=$1
  local sns=$2
  local ftime=$3
  spack_compilers
  chown -R ec2-user:ec2-user /fsx/run
  systemd_units
  slurm_db $region
  fini $region $sns $ftime
}

spack_compilers() {
  spack load intel-oneapi-compilers
  spack compiler find
  spack unload
  mkdir -p ~ec2-user/.spack/linux
  cp ~/.spack/linux/compilers.yaml ~ec2-user/.spack/linux
  chown -R ec2-user:ec2-user ~ec2-user/.spack
}

systemd_units() {

  cat > /etc/systemd/system/slurmdbd.service <<- EOF
	[Unit]
	Description=SlurmDBD daemon
	After=munge.service network.target
	ConditionPathExists=/opt/slurm/etc/slurmdbd.conf

	[Service]
	Type=simple
	Restart=always
	RestartSec=1
	User=root
	ExecStart=/opt/slurm/sbin/slurmdbd -D -s
	ExecReload=/bin/kill -HUP \$MAINPID
	LimitNOFILE=65536

	[Install]
	WantedBy=multi-user.target
EOF

  cat > /etc/systemd/system/slurmrestd.service <<- EOF
	[Unit]
	Description=Slurm REST daemon
	After=network.target munge.service slurmctld.service
	ConditionPathExists=/opt/slurm/etc/slurm.conf
	Documentation=man:slurmrestd(8)

	[Service]
	Type=simple
	User=slumrestd
	Group=slumrestd
	Environment="SLURM_JWT=daemon"
	ExecStart=/opt/slurm/sbin/slurmrestd -a rest_auth/jwt 0.0.0.0:8080
	ExecReload=/bin/kill -HUP \$MAINPID

	[Install]
	WantedBy=multi-user.target
EOF

  groupadd -r slumrestd
  useradd -r -c 'SLURM REST API user' -g slumrestd slumrestd
  systemctl enable slurmdbd.service
  systemctl enable slurmrestd.service
}

slurm_db() {
  local region=$1
  yum install -y mysql
  aws secretsmanager get-secret-value \
    --secret-id SlurmDbCreds \
    --query 'SecretString' \
    --region $region \
    --output text > /tmp/dbcreds
  export DBHOST=$(jq -r '.host' /tmp/dbcreds)
  export DBPASSWD=$(jq -r '.password' /tmp/dbcreds)
  rm /tmp/dbcreds

  cat > /opt/slurm/etc/slurmdbd.conf <<- EOF
	ArchiveEvents=yes
	ArchiveJobs=yes
	ArchiveResvs=yes
	ArchiveSteps=no
	ArchiveSuspend=no
	ArchiveTXN=no
	ArchiveUsage=no
	AuthType=auth/munge
	AuthAltTypes=auth/jwt
	AuthAltParameters=jwt_key=/opt/slurm/etc/jwt_hs256.key
	DbdHost=$(hostname)
	DbdPort=6819
	DebugLevel=info
	PurgeEventAfter=1month
	PurgeJobAfter=12month
	PurgeResvAfter=1month
	PurgeStepAfter=1month
	PurgeSuspendAfter=1month
	PurgeTXNAfter=12month
	PurgeUsageAfter=24month
	SlurmUser=slurm
	LogFile=/var/log/slurmdbd.log
	PidFile=/var/run/slurmdbd.pid
	StorageType=accounting_storage/mysql
	StorageUser=admin
	StoragePass=${DBPASSWD}
	StorageHost=${DBHOST}
	StoragePort=3306
EOF

  chmod 600 /opt/slurm/etc/slurmdbd.conf
  chown slurm:slurm /opt/slurm/etc/slurmdbd.conf

  dd if=/dev/urandom of=/opt/slurm/etc/jwt_hs256.key bs=32 count=1
  chmod 600 /opt/slurm/etc/jwt_hs256.key
  chown slurm:slurm /opt/slurm/etc/jwt_hs256.key

  cat >> /opt/slurm/etc/slurm.conf <<- EOF
	AuthAltTypes=auth/jwt
	AuthAltParameters=jwt_key=/opt/slurm/etc/jwt_hs256.key
	# ACCOUNTING
	JobAcctGatherType=jobacct_gather/linux
	JobAcctGatherFrequency=30
	#
	AccountingStorageType=accounting_storage/slurmdbd
	AccountingStorageHost=$(hostname)
	AccountingStorageUser=admin
	AccountingStoragePort=6819
EOF

  systemctl start slurmdbd.service
  systemctl start slurmrestd.service
}

fini() {
  local region=$1
  local sns=$2
  local ftime=$3
  local y=${ftime:0:4}
  local m=${ftime:5:2}
  local d=${ftime:8:2}
  local h=${ftime:11:2}

  cat > /tmp/jwt.sh <<-EOF
	#!/bin/bash

	. /etc/profile.d/slurm.sh
	cd /fsx/run
	echo $ftime > /fsx/run/ftime
	/fsx/run/get_gfs
	sudo systemctl restart slurmctld.service
	sleep 15
	aws secretsmanager update-secret \
	  --region ${region} \
	  --secret-id "JWTKey" \
	  --secret-string \$(/opt/slurm/bin/scontrol token lifespan=7200 | cut -f 2 -d = )

	export ip=$(curl -q -s http://169.254.169.254/latest/meta-data/local-ipv4)
	aws sns publish \
	  --region ${region} \
	  --subject "Parallel Cluster Post Install - SUCCESS" \
	  --message "\$ip" \
	  --topic-arn $sns

EOF
  chmod 755 /tmp/jwt.sh
  chown ec2-user:ec2-user /tmp/jwt.sh
  cat > /etc/systemd/system/jwt.service <<- EOF
	[Unit]
	Description=JWT generation
	After=slurmctld.service

	[Service]
	Type=simple
	User=ec2-user
	Group=ec2-user
	ExecStart=/tmp/jwt.sh
	WorkingDirectory=/tmp

	[Install]
	WantedBy=multi-user.target
EOF
  systemctl enable jwt.service
  systemctl start jwt.service
}

main $@
