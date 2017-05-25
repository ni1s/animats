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

# import networkx as nx
#from networkx.drawing.nx_agraph import graphviz_layout
import pygraphviz as pgv
import matplotlib.pyplot as plt
import Tkinter as tk
from Tkinter import PhotoImage
import network as Network
import os.path

from nodes import *
from sensor import *

COUNTER = 0

tk_root = tk.Tk()
tk_root.title('Animat')
tk_root.update()

# TODO: Dummy way to initialize the window, didn't have time to make it proper.
img = tk.PhotoImage(file='nets/start.gif')

# get the image size
w = img.width()
h = img.height()

# position coordinates of root 'upper left corner'
x = 0
y = 0

# make the root window the size of the image
tk_root.geometry("%dx%d+%d+%d" % (w, h, x, y))

panel1 = tk.Label(tk_root, image=img)
panel1.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

tk_root.update()

def plot(network, path=None):
    G=pgv.AGraph(directed=True)
    nodes = dict(enumerate(network.nodes.values()))
    edges = []

    for k,v in nodes.items(): v.__nx_id__ = k+1
    for k,v in nodes.items():
        if len(v.inputs) == 0:
            edges.append( (0, v.name) )
#            edges.append( (0, v.n_id) )
        for i in v.inputs:
            edges.append( (i.name, v.name) )
#            edges.append( (i.n_id, v.n_id) )

#    print nodes, edges

    G.add_node(0)
    for k,v in nodes.items():
        d = {}
        if v.__class__ == SensorNode:
            d['shape']='square'
        elif v.__class__ == NAndNode:
            d['shape']='triangle'
        if v.active:
            d['fillcolor']='pink'
            d['style']='filled'
        if v.isTopNode():
            d['color']='green'
        if v.isTopActive():
            d['fillcolor']='red'
            d['style']='filled'

        G.add_node(v.name, **d)
#        G.add_node(v.n_id, **d)
#    G.add_nodes_from(sorted(nodes.values()))
    G.add_edges_from(edges)

    plt.clf()
    G.layout(prog='dot')
    filename = os.path.join( path, "net_%d.gif" % network.time )
    G.draw(filename)

    # sips -Z 640 *.jpg
    img2 = tk.PhotoImage(file=filename)
    panel1.configure(image=img2)
    panel1.update()

    # plt.show()
    #plt.show(block=False)
