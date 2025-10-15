"""
Service de Planification avec APScheduler
Gère les tâches périodiques (scan auto, nettoyage, etc.)
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Callable, Dict
import logging


class SchedulerService:
    """Service de planification des tâches périodiques"""
    
    def __init__(self):
        """Initialise le scheduler"""
        self.scheduler = BackgroundScheduler(
            daemon=True,
            timezone='UTC',
            job_defaults={
                'coalesce': True,
                'max_instances': 1
            }
        )
        
        # Configurer le logging
        logging.getLogger('apscheduler').setLevel(logging.WARNING)
        
        self.jobs = {}
        
        print("✅ SchedulerService initialisé")
    
    def start(self):
        """Démarre le scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            print("✅ Scheduler démarré")
    
    def stop(self):
        """Arrête le scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            print("✅ Scheduler arrêté")
    
    def add_interval_job(self, job_id: str, func: Callable, 
                        interval_seconds: int, **kwargs):
        """Ajoute un job avec intervalle fixe"""
        try:
            if job_id in self.jobs:
                self.remove_job(job_id)
            
            job = self.scheduler.add_job(
                func=func,
                trigger=IntervalTrigger(seconds=interval_seconds),
                id=job_id,
                name=job_id,
                replace_existing=True,
                kwargs=kwargs
            )
            
            self.jobs[job_id] = {
                'job': job,
                'type': 'interval',
                'interval': interval_seconds,
                'func': func.__name__
            }
            
            print(f"✅ Job ajouté: {job_id} (toutes les {interval_seconds}s)")
            return True
            
        except Exception as e:
            print(f"❌ Erreur add_interval_job: {e}")
            return False
    
    def add_cron_job(self, job_id: str, func: Callable, 
                    cron_expression: str, **kwargs):
        """Ajoute un job avec expression cron"""
        try:
            if job_id in self.jobs:
                self.remove_job(job_id)
            
            job = self.scheduler.add_job(
                func=func,
                trigger=CronTrigger.from_crontab(cron_expression),
                id=job_id,
                name=job_id,
                replace_existing=True,
                kwargs=kwargs
            )
            
            self.jobs[job_id] = {
                'job': job,
                'type': 'cron',
                'cron': cron_expression,
                'func': func.__name__
            }
            
            print(f"✅ Job cron ajouté: {job_id} ({cron_expression})")
            return True
            
        except Exception as e:
            print(f"❌ Erreur add_cron_job: {e}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """Supprime un job"""
        try:
            if job_id in self.jobs:
                self.scheduler.remove_job(job_id)
                del self.jobs[job_id]
                print(f"✅ Job supprimé: {job_id}")
                return True
            else:
                print(f"⚠️ Job non trouvé: {job_id}")
                return False
        except Exception as e:
            print(f"❌ Erreur remove_job: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """Met en pause un job"""
        try:
            if job_id in self.jobs:
                self.scheduler.pause_job(job_id)
                print(f"⏸️ Job en pause: {job_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Erreur pause_job: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """Reprend un job en pause"""
        try:
            if job_id in self.jobs:
                self.scheduler.resume_job(job_id)
                print(f"▶️ Job repris: {job_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Erreur resume_job: {e}")
            return False
    
    def get_job_info(self, job_id: str) -> Dict:
        """Récupère les infos d'un job"""
        if job_id not in self.jobs:
            return None
        
        job_data = self.jobs[job_id]
        job = job_data['job']
        
        return {
            'id': job_id,
            'name': job.name,
            'type': job_data['type'],
            'func': job_data['func'],
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'interval': job_data.get('interval'),
            'cron': job_data.get('cron')
        }
    
    def get_all_jobs(self) -> Dict:
        """Liste tous les jobs actifs"""
        jobs_info = {}
        for job_id in self.jobs:
            jobs_info[job_id] = self.get_job_info(job_id)
        return jobs_info
    
    def execute_job_now(self, job_id: str) -> bool:
        """Exécute immédiatement un job"""
        try:
            if job_id in self.jobs:
                job = self.jobs[job_id]['job']
                job.modify(next_run_time=datetime.now())
                print(f"🔥 Exécution immédiate: {job_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Erreur execute_job_now: {e}")
            return False