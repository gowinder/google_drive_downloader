from tornado import gen, ioloop, queues
import random
import json

class fake_msg:
    def __init__(self, i, value):
        super().__init__()
        self.i = i
        self.value = []
        self.value.append(value)

fake_list = dict()

async def fake_maintainer(main_queue:queues.Queue, maintain_queue:queues.Queue):

    worker_queue = list()
    for _ in range(concurrency):
        worker_queue.append(queues.Queue())
    f = gen.multi([fake_worker(i, worker_queue[i], maintain_queue) for i in range(concurrency)])

    async for msg in maintain_queue:
        try:
            if msg.i not in fake_list:
                fake_list[msg.i] = fake_msg(msg.i, msg.value)
            else:                            
                fake_list[msg.i].value.append(msg.value)
            await gen.sleep(0.01)
        finally:
            maintain_queue.task_done()

    # print('maintainer get order')
    # for q in worker_queue:
    #     f.cancel()

    print('maintainer end')

async def fake_worker(i, q:queues.Queue, maintain_queue:queues.Queue):
    print('fake worker {} started...'.format(i))
    round = 1
    while True:
        try:
            w = random.randint(1, 100) / 100
            putvalue = random.randrange(0, 100)
            # print('{} round {}, wait {} put value {}'.format(i, round, w, putvalue))
            round += 1
            await gen.sleep(w)
            await maintain_queue.put(fake_msg(i, putvalue))
        except queues.QueueEmpty:
            continue
    
    print('fake worker {} end...'.format(i))


concurrency = 10