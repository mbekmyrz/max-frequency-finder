import networkx as nx
import matplotlib.pyplot as plt
import xml.etree.ElementTree as Tree


class Node:
    def __init__(self, name, delay, edgeIn, edgeOut):
        self.__nodeName = name
        self.__propagationDelay = delay
        self.__edgesIn = edgeIn
        self.__edgesOut = edgeOut
        self.__x = 0
        self.__y = 0

    @property
    def nodeName(self):
        return self.__nodeName

    @nodeName.setter
    def nodeName(self, name):
        self.__nodeName = name

    @property
    def propagationDelay(self):
        return self.__propagationDelay

    @propagationDelay.setter
    def propagationDelay(self, delay):
        self.__propagationDelay = delay

    @property
    def edgesIn(self):
        return self.__edgesIn

    @edgesIn.setter
    def edgesIn(self, edgeIn):
        self.__edgesIn = edgeIn

    @property
    def edgesOut(self):
        return self.__edgesOut

    @edgesOut.setter
    def edgesOut(self, edgeOut):
        self.__edgesOut = edgeOut

    @property
    def x(self):
        return self.__x

    @x.setter
    def x(self, x):
        self.__x = x

    @property
    def y(self):
        return self.__y

    @y.setter
    def y(self, y):
        self.__y = y


class Gate(Node):
    def __init__(self, name, delay, edgeIn, edgeOut):
        super().__init__(name, delay, edgeIn, edgeOut)


class FlipFlop(Node):
    def __init__(self, name, delay, setup, hold, edgeIn, edgeOut):
        super().__init__(name, delay, edgeIn, edgeOut)
        self.__setupTime = setup
        self.__holdTime = hold

    @property
    def setupTime(self):
        return self.__setupTime

    @setupTime.setter
    def setupTime(self, setup):
        self.__setupTime = setup

    @property
    def holdTime(self):
        return self.__holdTime

    @holdTime.setter
    def holdTime(self, hold):
        self.__holdTime = hold


class Netlist(nx.DiGraph):
    def __init__(self, file):
        super().__init__()
        self.ffPaths = []
        self.comboPaths = []
        self.gfPaths = []
        self.fMax = 0
        self.comboMax = 0
        tree = Tree.parse(file)
        root = tree.getroot()
        for element in root:
            if element.attrib["type"] == "FF":
                self.add_node(FlipFlop(element.attrib["name"], float(element.find("propagationDelay").text),
                                       float(element.find("setupTime").text),
                                       float(element.find("holdTime").text),
                                       element.find("input").text.split(","),
                                       element.find("output").text.split(",")))
            elif element.attrib["type"] == "GATE":
                self.add_node(Gate(element.attrib["name"], float(element.find("propagationDelay").text),
                                   element.find("input").text.split(","),
                                   element.find("output").text.split(",")))
        inputError = False
        for node1 in self.nodes:
            if type(node1) == FlipFlop and len(node1.edgesIn) > 1:
                inputError = True
                print("More than one input to ", node1.nodeName)
            elif type(node1) == Gate and len(node1.edgesIn) > 2:
                inputError = True
                print("More than two input to ", node1.nodeName)
            elif len(node1.edgesIn) < 1 or len(node1.edgesOut) < 1:
                inputError = True
                print("No input/output specified ", node1.nodeName)
            else:
                for node2 in self.nodes:
                    if node1 is not node2:
                        for edgeOut in node1.edgesOut:
                            if edgeOut in node2.edgesIn:
                                self.add_edge(node1, node2)
        if inputError:
            print("Fix the errors. Program is exiting... ")
            exit()

    def containsFF(self, path):
        for i in range(1, len(path)-1):
            if type(path[i]) == FlipFlop:
                return True
        return False

    def timingAnalyze(self):
        for sourceNode in self.nodes:
            if not len(list(self.successors(sourceNode))) == 0:
                # if sourceNode is FF, search for next flip flop - endNode
                if type(sourceNode) == FlipFlop:
                    for targetNode in self.nodes:
                        if type(targetNode) == FlipFlop and sourceNode is not targetNode:
                            for path in nx.all_simple_paths(self, source=sourceNode, target=targetNode):
                                if not len(path) == 0 and not self.containsFF(path):
                                    self.ffPaths.append(path)
                # if sourceNode is starting Gate Node, search for last Gate Node - endNode
                elif len(list(self.predecessors(sourceNode))) == 0 and type(sourceNode) == Gate:
                    for targetNode in self.nodes:
                        if len(list(self.successors(targetNode))) == 0 and type(targetNode) == Gate\
                                and sourceNode is not targetNode:
                            for path in nx.all_simple_paths(self, source=sourceNode, target=targetNode):
                                if not len(path) == 0 and not self.containsFF(path):
                                    self.comboPaths.append(path)
                        if type(targetNode) == FlipFlop:
                            for path in nx.all_simple_paths(self, source=sourceNode, target=targetNode):
                                if not len(path) == 0 and not self.containsFF(path):
                                    self.gfPaths.append(path)
        print(100 * "-")
        for path in self.ffPaths:
            print("FF-to-FF Path:", [x.nodeName for x in path])
            total = 0
            for node in path:
                if not path.index(node) == len(path) - 1:
                    total += node.propagationDelay
                else:
                    total += node.setupTime
            if total > self.fMax:
                self.fMax = total
        print(100 * "-")
        self.fMax = 1/self.fMax
        for path in self.comboPaths:
            print("Pure Combo Path:", [x.nodeName for x in path])
            total = 0
            for node in path:
                total += node.propagationDelay
            if total > self.comboMax:
                self.comboMax = total
        print(100 * "-")
        for path in self.gfPaths:
            total = 0
            for node in path:
                if not path.index(node) == len(path) - 1:
                    total += node.propagationDelay
                elif 1/self.fMax - total < node.setupTime:
                    print("Setup time is not satisfied on gate-to-flipflop path:", path[0].nodeName,
                          node.nodeName)
            print("Setup time is satisfied on gate-to-flipflop path:", path[0].nodeName, path[len(path)-1].nodeName)
        print(100 * "-")
        print("The fMax: ", self.fMax)
        print("The Combo Max: ", self.comboMax)
        print(100 * "-")

    def position(self, node, x, y):
        for nextNode in list(self.successors(node)):
            x += 1
            if nextNode.x == 0 and nextNode.y == 0:
                nextNode.x = x
                nextNode.y = y
            self.position(nextNode, nextNode.x, nextNode.y)
            y += 1

    def draw(self):
        labels, pos = {}, {}
        node_color = ""
        size = []
        y = 0
        for node in self.nodes:
            labels[node] = node.nodeName
            if node.x == 0 and node.y == 0:
                node.y = y
                self.position(node, node.x, node.y)
                y += 1
            if type(node) == FlipFlop:
                node_color += "r"
            else:
                node_color += "c"

            pos[node] = (node.x, node.y)
            size.append(len(node.nodeName)*180)

        """
        startNodes = []
        endNodes = []
        for node in self.nodes:
            if len(list(self.predecessors(node))) == 0:
                startNodes.append(node)
            elif len(list(self.successors(node))) == 0:
                endNodes.append(node)
        paths = []
        for sourceNode in startNodes:
            for targetNode in endNodes:
                for path in nx.all_simple_paths(self, source=sourceNode, target=targetNode):
                    paths.append(path)
        """

        nx.draw(self, node_size=size, pos=pos, node_color=node_color, labels=labels, font_size=10, with_labels=True)
        plt.savefig('graph.png')


myCircuit = Netlist("graph.xml")
myCircuit.timingAnalyze()
myCircuit.draw()

