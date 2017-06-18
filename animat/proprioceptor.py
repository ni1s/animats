# -*- coding: utf-8 -*-
#
#    pyAnimat - Simulate Animats using Transparent Graphs as a way to AGI
#    Copyright (C) 2017  David Lindström
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from node import *


class ProprioceptorNode(Node):
    def __init__(self, name, sensor, agent=None):
        Node.__init__(self, name, permanent=True)
        self.agent = agent
        self.sensor = sensor

    def tick(self, time):
        state = False
        if Node.tick(self, time):
            # set sensor active if the related motor was selected as the last action
            sensor_state = self.readSensor()
            if sensor_state != None:
                if (sensor_state == self.sensor):
                    self.activate(time)
                else:
                    self.deactivate(time)
            return True
        else:
            return False

    def addAgent(self, agent):
        self.agent = agent

    def readSensor(self):
        if len(self.agent.trail) > 0:
            return self.agent.trail[-1][1]
        else:
            return None
