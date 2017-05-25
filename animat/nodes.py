# -*- coding: utf-8 -*-
#
#    pyAnimat - Simulate Animats using Transparent Graphs as a way to AGI
#    Copyright (C) 2017  Nils Svangård, Claes Strannegård
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

def truth(v):
    on = 0
    off = 0
    total = 0
    for x in v:
        if x: on = on + 1
        else: off = off + 1
        total = total + 1
    return (on, off, total)

class AndNode(Node):
    def __init__(self, name=None, inputs=[], outputs=[],permanent=False,virtual=False):
        inputs = sorted(inputs, key=lambda x: x.name)
        if not name: name = makeName("AND", inputs)
        Node.__init__(self, name, inputs, outputs, permanent, virtual)

    def tick(self, time):
        if Node.tick(self, time):
            v = [node.active for node in self.inputs]
            on, off, total = truth(v)
            if total > 0 and total == on:
                self.activate(time)
            else:
                self.deactivate(time)
            return True
        else:
            return False

class NAndNode(Node):
    def __init__(self, name=None, inputs=[], outputs=[], permanent=False):
        inputs = sorted(inputs, key=lambda x: x.name)
        if not name: name = makeName("NAND", inputs)
        Node.__init__(self, name, inputs, outputs, permanent)

    def tick(self, time):
        if Node.tick(self, time):
            v = [node.active for node in self.inputs]
            on, off, total = truth(v)
            if total > 0 and total == on:
                self.deactivate(time)
            else:
                self.activate(time)
            return True
        else:
            return False

class SEQNode(Node):
    def __init__(self, name=None, inputs=[], outputs=[],permanent=False,virtual=False):
        if not name: name = makeName("SEQ", inputs, sort=False)
        Node.__init__(self, name, inputs, outputs, permanent, virtual)

    def tick(self, time):
        if Node.tick(self, time):
            if len(self.inputs) > 1:
                if self.inputs[0].wasActive() and self.inputs[1].isActive():
                    self.activate(time)
                else:
                    self.deactivate(time)
            return True
        else:
            return False

# TODO: must update tick code...
#
# class OrNode(Node):
#     def __init__(self, name=None, inputs=[], outputs=[]):
#         if not name: name = "or(%s) -> (%s)" %(",".join([i.name for i in inputs]), ",".join([o.name for o in outputs]))
#         Node.__init__(self, name, inputs, outputs)
#
#     def tick(self, time):
#         if self.time >= time: return self.active
#         v = [node.tick(time) for node in self.inputs]
#         on, off, total = truth(v)
#         if on > 0:
#             self.activate(time)
#         else:
#             self.deactivate(time)
#         return self.active
