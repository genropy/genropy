from gnr.web.batch.btcaction import BaseResourceAction


caption = 'Execute data cleanup'
description = 'Execute data cleanup and retention policies'
tags = 'admin'

class Main(BaseResourceAction):
    batch_prefix = 'retentioncleanup'
    batch_title = 'Execute data cleanup'
    batch_steps = 'main'
    batch_cancellable = False
    
    def step_main(self):
        self.db.application.executeRetentionPolicy(dry_run=False)

    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div('!!Records older than the retention policies allow will be permanently deleted.',
                 font_style='italic', color='#666', padding='10px')
