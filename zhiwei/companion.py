"""安静陪伴优先：动作轮换有间隔，移动稀疏且不跨屏。"""
import random
import time

class CompanionRoutine:
    DURATIONS={'daydream':(45,90),'swing':(60,120),'play':(16,26),'tired':(25,45),'drink':(10,16)}
    def __init__(self,pet):
        self.pet=pet;self.previous=None;self.bag=[];self.active=False
        self.due=time.monotonic()+random.uniform(25,45)
        self.last_move=-1000
    def resume(self,delay=15):
        self.active=False;self.due=time.monotonic()+delay
    def choose(self,now):
        if not self.pet.store.get('roam',True):
            self.bag=[a for a in self.bag if a!='walk']
        if not self.bag:
            self.bag=['daydream','swing','play','tired','drink']
            if self.pet.store.get('roam',True):self.bag.append('walk')
            random.shuffle(self.bag)
        # 不丢弃暂时不可用的移动，其他动作都有机会被执行。
        for index,action in enumerate(self.bag):
            if action==self.previous:continue
            if action=='walk' and (not self.pet.store.get('roam',True) or now-self.last_move<180):continue
            self.bag.pop(index);return action
        return 'daydream'
    def tick(self,now):
        p=self.pet
        if p.dock_side or p.collapsed or p.drag_origin is not None or p.quick_active() or p.fan.isVisible() or p.store.get('quiet',False) or p.store.get('focus'):
            self.due=max(self.due,now+15);return
        if p.state!='idle':return
        if self.active:
            self.active=False;self.due=now+random.uniform(35,65);return
        if now<self.due:return
        action=self.choose(now);self.previous=action;self.active=True
        if action=='walk':
            self.last_move=now
            # 只在附近窗边做短暂探头；不追逐远处窗口。
            if random.random()<.2 and p.can_peek_nearby():p.peek(automatic=True)
            else:p.walk()
        else:
            low,high=self.DURATIONS[action]
            p.react(action,duration=random.uniform(low,high),speak=False)
