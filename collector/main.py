import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from nasa_neows import collect_neows
from nasa_donki import collect_cme, collect_gst

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Coleta imediata na inicialização
collect_neows()
collect_cme()
collect_gst()

# Agenda diária às 00:30 UTC
scheduler = BlockingScheduler()
scheduler.add_job(collect_neows, "cron", hour=0, minute=30)
scheduler.add_job(collect_cme, "cron", hour=0, minute=35)
scheduler.add_job(collect_gst, "cron", hour=0, minute=40)

scheduler.start()
