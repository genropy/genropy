from gnr.web.batch.btcaction import BaseResourceAction


caption = 'Execute data cleanup'
description = 'Execute data cleanup and retention policies'
tags = 'admin'

class Main(BaseResourceAction):
    batch_prefix = 'retentioncleanup'
    batch_title = 'Execute data cleanup'
    batch_steps = 'main'
    batch_cancellable = False
    
    def steps_main(self):
        self.db.application.executeRetentionPolicy(dry_run=False)
