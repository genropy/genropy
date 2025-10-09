#  -*- coding: utf-8 -*-
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:BaseRpc'

    @public_method(tags='_async_scheduler_') #tag di autorizzazione dell'utente 
    def proxy_sync(self):
        # 1. riceve il delivery_report
        #   1.1 aggiorna i messaggi che sono stati spediti o che sono andati in errore
        # 2. cerca i messaggi da spedire
        # 3. ne prende il massimo prefissato esempio 100
        # 4. fa una chiamata al proxy add_messages 
        # 5. attende dal proxy come risposta i messaggi eventualmente rifiutati
        # 6. aggiorna sul db i messaggi accettati col flag sending
        # 7. quelli rifiutati vengono marcati con erro_ts
        
        pass

