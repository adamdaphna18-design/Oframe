import time,yaml,subprocess,random
from datetime import datetime
class AdaptiveScheduler:
    def __init__(self,path='schedules.yaml'):
        with open(path) as f:self.config=yaml.safe_load(f)
    def run(self):
        print('Scheduler running')
        while True:
            for s in self.config.get('schedules',[]):
                if s.get('trigger')=='interval':
                    print(f'Would run {s.get("skill")}')
            time.sleep(30)
if __name__=='__main__':AdaptiveScheduler().run()
