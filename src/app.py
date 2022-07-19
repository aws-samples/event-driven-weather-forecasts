#!/usr/bin/env python3

import aws_cdk as cdk

from wx.root import Root

app = cdk.App()

wx = Root(app, 'WX')
cdk.Tags.of(wx).add("Purpose", "Event Driven Weather Forecast", priority=300)

app.synth()
