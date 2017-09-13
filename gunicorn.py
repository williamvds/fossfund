"""Gunicorn config"""
import multiprocessing

bind = 'localhost:8080'
proxy_allow_from = 'localhost,127.0.0.1'
forwarded_allow_ips = 'localhost,127.0.0.1'
workers = multiprocessing.cpu_count()
worker_class='aiohttp.worker.GunicornWebWorker'
