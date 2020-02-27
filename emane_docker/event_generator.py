#!/usr/bin/env python


from time import sleep

import numpy as np
from emane.events import EventService
from emane.events import PathlossEvent
from emane.events import LocationEvent

from emane_docker.distribution import DistributionParser
from emane_docker.log import LOG


class EventGenerator:
    """
    Generates EMANE Events.

    :param nodes: The list of nodes.
    :param link_update: Link update configuration.
    :param duration: Duration of the experiment.
    """

    def __init__(self, nodes, link_update, duration):
        self.nodes = nodes
        self.duration = duration
        self.distribution = DistributionParser(distribution=link_update)
        self.event_service = EventService(('224.1.2.8', 45703, 'emanenode0'))

    def _create_bi_pathloss(self, nem1, nem2, db1, db2):
        event = PathlossEvent()
        event.append(nem1, forward=db1)
        event.append(nem2, forward=db2)
        self.event_service.publish(nem1, event)
        self.event_service.publish(nem2, event)

    def _create_pathloss(self, nem1, nem2, db):
        self._create_bi_pathloss(nem1, nem2, db, db)

    def _create_location(self, latitude, longitude, altitude):
        event = LocationEvent()
        event.append(1, latitude=latitude, longitude=longitude, altitude=altitude)
        self.event_service.publish(0, event)

    def _pick_random_nem(self):
        return int(np.random.choice(self.nodes.keys()).split('-')[1])

    def _pick_random_db(self, is_binary):
        if is_binary:
            if np.random.random() < 0.5:
                return 0
            return 200

        return np.random.random() * 100

    def start(self):
        i = 0
        while self.distribution.start_next_simulation():
            LOG.info('Starting a new simulation')
            current_time = 0
            print('sim number %d' % i)
            while True:
                next_event_time = self.distribution.get_next()
                sleep(next_event_time)
                print(current_time, next_event_time, current_time + next_event_time)
                current_time += next_event_time
                if current_time > self.duration:
                    break
                nem2 = nem1 = self._pick_random_nem()
                while nem1 == nem2:
                    nem2 = self._pick_random_nem()
                db = self._pick_random_db(is_binary=True)
                LOG.debug('New pathloss update at %f: node-%s node-%s %d', current_time, nem1, nem2,
                          db)
                self._create_pathloss(nem1, nem2, db)
            i += 1


if __name__ == "__main__":
    print('Please run it using emane-docker.')
