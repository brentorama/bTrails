import das

class Blaze(object):

    def __init__(self, name="trail", sections=5, p=None, emit=None, frange=[]):
        super(Blaze, self).__init__()

        self.emit = emit
        self.p = p
        self.nodes = das.Struct()
        self.nodes.curves = das.Struct()
        self.nodes.lofts = []
        self.nodes.choiceNodes = []
        self.nodes.rangeNodes = []
        self.name = name
        self.maxDiv = 0
        self.sections = sections

        if not frange:
            frange=self.getfrange()
            
        self.frange = frange


    def getfrange(self):
        frange = (maya.cmds.playbackOptions(q=True, min=True), 
                  maya.cmds.playbackOptions(q=True, max=True))
        return frange


    def build(self):

        grup = maya.cmds.group(em=True, n="curvegrup")
        curv = maya.cmds.createNode("nurbsCurve",           n="%s_curv" % self.name)
        surf = maya.cmds.createNode("nurbsSurface",         n="%s_SURF" % self.name)
        loft = maya.cmds.createNode("loft",                 n="%s_OUT" % self.name)
        cfos = maya.cmds.createNode("curveFromSurfaceIso",  n="%s_cfos" % self.name)
        addl = maya.cmds.createNode("addDoubleLinear" ,     n="%s_add" % self.name)
        plmn = maya.cmds.createNode("plusMinusAverage",     n="%s_minus" % self.name)
        mult = maya.cmds.createNode("multiplyDivide",       n="%s_multi" % self.name)
        five = maya.cmds.createNode("addDoubleLinear",      n="%s_pointFive" % self.name)

        maya.cmds.addAttr(curv, ln="frame", at="float", min = self.frange[0]-2, max = self.frange[1]+2, k=True)
        maya.cmds.addAttr(curv, ln="floor", at="long", k=True)

        maya.cmds.connectAttr("%s.outputSurface" % loft, "%s.create" % surf )
        maya.cmds.connectAttr("%s.outputSurface" % loft, "%s.inputSurface" % cfos )
        maya.cmds.connectAttr("%s.outputCurve" % cfos, "%s.create" % curv )
        maya.cmds.connectAttr("%s.frame" % curv, "%s.input1" % addl)
        maya.cmds.connectAttr("%s.output" % addl, "%s.floor" % curv)
        maya.cmds.connectAttr("%s.frame" % curv, "%s.input1D[0]" % plmn)
        maya.cmds.connectAttr("%s.floor" % curv, "%s.input1D[1]" % plmn)
        maya.cmds.connectAttr("%s.output1D" % plmn, "%s.input1X" % mult)
        maya.cmds.connectAttr("%s.outputX" % mult, "%s.input1" % five)
        maya.cmds.connectAttr("%s.output" % five, "%s.isoparmValue" % cfos)

        maya.cmds.setAttr("%s.isoparmDirection" % cfos, 1)
        maya.cmds.setAttr("%s.relativeValue" % cfos, 1)
        maya.cmds.setAttr("%s.input2" % addl, -0.5)
        maya.cmds.setAttr("%s.operation" % plmn, 2)
        maya.cmds.setAttr("%s.operation" % mult, 2)
        maya.cmds.setAttr("%s.input2X" % mult, sections)
        maya.cmds.setAttr("%s.input2" % five, 0.5)
        maya.cmds.setAttr("%s.dispCV" % curv, 1)
        
        transform = maya.cmds.listRelatives(surf, p=True)[0]
        maya.cmds.parent(transform, grup)

        nodes = {   "group" : grup,
                    "curve" : curv,
                    "surface" : surf,
                    "loft" : loft,
                    "curveFromSurface" : cfos,
                    "addLinear" : addl,
                    "minus" : plmn,
                    "divide" : mult,
                    "pointFive" : five}

        for node in nodes:
            self.nodes[node] = nodes[node]
 

    def draw(self, verbose=False, dryrun=False):
        frame = maya.cmds.currentTime(q=True)
        cid=0
        prepend = []
        for i in range(int(self.frange[0]-2), int(self.frange[1]+2)):
            maya.cmds.refresh(su=True)
            maya.cmds.currentTime(i)
            particles = maya.cmds.getAttr("%s.position" % p) or []
            basePos = maya.cmds.getAttr("%s.t" % self.emit)[0]

            if not particles:
                prepend =  [maya.cmds.getAttr("%s.t" % emit, time=(self.frange[0]-1))[0], 
                            maya.cmds.getAttr("%s.t" % emit, time=(self.frange[0]-2))[0],
                            maya.cmds.getAttr("%s.t" % emit, time=(self.frange[0]-3))[0]]
            if prepend:
                particles.insert(0, prepend[0])
                particles.insert(0, prepend[1])
                particles.insert(0, prepend[2])

            particles.append(basePos)
            particles.reverse()
            c = maya.cmds.curve(p = particles)
            d = {   "shape" : maya.cmds.listRelatives(c, s=True)[0],
                    "id" : cid}
            cid += 1
            self.nodes.curves[c] = d
            maya.cmds.parent(c, self.nodes.group)
            self.maxDiv = maya.cmds.getAttr("%s.spans" % c)

        numCurves = len(self.nodes.curves)

        for i in range(sections):
            chNode = maya.cmds.createNode("choice", n="%s_%02d" % ("choice", i))
            raNode = maya.cmds.createNode("setRange", n="%s_%02d" % ("setRange", i))
            self.nodes.choiceNodes.append(chNode)
            self.nodes.rangeNodes.append(raNode)

            maya.cmds.setAttr("%s.oldMinX" % raNode, self.frange[0])
            maya.cmds.setAttr("%s.oldMaxX" % raNode, numCurves-sections)
            maya.cmds.setAttr("%s.minX" % raNode, i)
            maya.cmds.setAttr("%s.maxX" % raNode, numCurves+i-sections)

            maya.cmds.connectAttr("%s.floor" % self.nodes.curve, "%s.valueX" % raNode)
            maya.cmds.connectAttr("%s.outValueX" % raNode, "%s.selector" % chNode)
            maya.cmds.connectAttr("%s.output" % chNode, "%s.inputCurve[%s]" % (self.nodes.loft, i))
            
            for c in self.nodes.curves:
                maya.cmds.rebuildCurve(c, s=self.maxDiv)
                id = self.nodes.curves[c].id
                shape = self.nodes.curves[c].shape
                maya.cmds.connectAttr("%s.worldSpace[0]" % shape, "%s.input[%s]" % (chNode, id))

        maya.cmds.setAttr("%s.v" % self.nodes.group, False)
        maya.cmds.setAttr("%s.frame" % self.nodes.curve, frame)
        maya.cmds.refresh(su=False)
        
        maya.cmds.currentTime(e=frame)
        maya.cmds.select(self.nodoes.curve)

        if verbose or dryrun:
            das.pprint(self.nodes)

trail = Blaze(p="nParticleShape1", emit="emitter1")
trail.build()
trail.draw()
