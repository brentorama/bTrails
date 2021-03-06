import das
class Blaze(object):

    def __init__(self, name="trail", p=None, emit=None, frange=[]):
        super(Blaze, self).__init__()

        self.emit = emit
        self.p = p
        self.nodes = das.Struct()
        self.nodes.curves = das.Struct()
        self.name = name
        self.maxDiv = 0
        self.reduce = 0.7

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
        mins = maya.cmds.createNode("addDoubleLinear",      n="%s_minus" % self.name)
        rebu = maya.cmds.createNode("rebuildCurve",         n="%s_rebuild" % self.name)
        choi = maya.cmds.createNode("choice",               n="%s_choice" % self.name)
        mult = maya.cmds.createNode("multiplyDivide",       n="%s_multiplier" % self.name)
        clmp = maya.cmds.createNode("clamp",                n="%s_clamp" % self.name)

        obj = maya.cmds.listRelatives(curv, p=True)[0]

        maya.cmds.addAttr(obj, ln="frame", at="float", min = self.frange[0], max = self.frange[1], k=True)
        maya.cmds.addAttr(obj, ln="multiplier", at="float", min = 1, max = 4, k=True)
        maya.cmds.addAttr(obj, ln="spanType", at="enum", en="frame:uniform:", k=True)
        maya.cmds.addAttr(obj, ln="count", at="long", min=3, k=True)
        maya.cmds.addAttr(obj, ln="curves", at="message")

        maya.cmds.connectAttr("%s.outputCurve" % cfos, "%s.inputCurve" % rebu )
        maya.cmds.connectAttr("%s.outputCurve" % rebu, "%s.create" % curv )
        maya.cmds.connectAttr("%s.outputSurface" % loft, "%s.create" % surf )
        maya.cmds.connectAttr("%s.outputSurface" % loft, "%s.inputSurface" % cfos )
        maya.cmds.connectAttr("%s.spanType" % obj, "%s.selector" % choi )
        maya.cmds.connectAttr("%s.frame" % obj, "%s.input1" % mins)
        maya.cmds.connectAttr("%s.count" % obj, "%s.input[1]" % choi)
        maya.cmds.connectAttr("%s.multiplier" % obj, "%s.input2X" % mult)
        maya.cmds.connectAttr("%s.output" % mins, "%s.isoparmValue" % cfos)
        maya.cmds.connectAttr("%s.output" % mins, "%s.inputR" % clmp)
        maya.cmds.connectAttr("%s.outputR" % clmp, "%s.input[0]" % choi)
        maya.cmds.connectAttr("%s.output" % choi, "%s.input1X" % mult)
        maya.cmds.connectAttr("%s.outputX" % mult, "%s.spans" % rebu)

        maya.cmds.setAttr("%s.isoparmDirection" % cfos, 1)
        maya.cmds.setAttr("%s.relativeValue" % cfos, 0)
        maya.cmds.setAttr("%s.maxR" % clmp, self.frange[1]+2)
        maya.cmds.setAttr("%s.minR" % clmp, 3)

        maya.cmds.setAttr("%s.dispCV" % curv, 1)
        maya.cmds.setAttr("%s.uniform" % loft, 1)
        maya.cmds.setAttr("%s.input2" % mins, -self.frange[0])
        
        
        transform = maya.cmds.listRelatives(surf, p=True)[0]
        maya.cmds.parent(transform, grup)

        nodes = {   "group" : grup,
                    "curve" : curv,
                    "ctl" : obj,
                    "surface" : surf,
                    "loft" : loft,
                    "curveFromSurface" : cfos,
                    "particle" : self.p,
                    "emitter" : self.emit}

        for node in nodes:
            maya.cmds.addAttr(obj, ln=node, at="message")
            try:
                maya.cmds.addAttr(nodes[node], ln=self.name, at="message")
            except:
                print("Bad Att")
            maya.cmds.connectAttr("%s.%s" % (obj, node), "%s.%s" % (nodes[node], self.name))
            self.nodes[node] = nodes[node]
 

    def getParticles(self, p=None, start=0, end=1):

        particles = {}
        maya.cmds.setAttr("%s.isDynamic" % p, True)

        for frame in range(start, end):
            maya.cmds.currentTime(frame)
            pPos = maya.cmds.getAttr("%s.position" % p) or []
            particles[frame] = pPos

        maya.cmds.setAttr("%s.isDynamic" % p, False)

        return particles


    def makeCurves(self, points=None, emit=None):
        curves = das.Struct()
        cid = 0
        for frame in points:

            for i in range(1,3):
                if len(points[frame]) < i:
                    wMatrix = maya.cmds.getAttr("%s.worldMatrix" % emit, time=(frame-i))
                    points[frame].insert(0, (wMatrix[12], wMatrix[13], wMatrix[14]))

            baseMat = maya.cmds.getAttr("%s.worldMatrix" % emit, time = frame+1)
            points[frame].append((baseMat[12], baseMat[13], baseMat[14]))
            points[frame].reverse()

            c = maya.cmds.curve(p = points[frame]) or None
            shape = maya.cmds.listRelatives(c, s=True) or []

            d = {   "shape" : shape[0],
                    "id" : cid}

            cid += 1
            curves[c] = d
            spans = maya.cmds.getAttr("%s.spans" % c)
            if spans > self.maxDiv:
                self.maxDiv = spans

        return curves



    def draw(self, verbose=False, dryrun=False):
        maya.cmds.refresh(su=True)

        frame = maya.cmds.currentTime(q=True)

        if self.nodes.curves:
            maya.cmds.delete(self.nodes.curves)

        particles = self.getParticles(start = int(self.frange[0]), end = int(self.frange[1]+1), p=self.p)
        curves = self.makeCurves(points=particles, emit=self.emit)
        self.nodes.curves = curves
        numCurves = len(self.nodes.curves)
            
        for c in self.nodes.curves:
            maya.cmds.addAttr(self.nodes.curves[c].shape, ln=self.name, at="message")
            maya.cmds.connectAttr("%s.curves" % self.nodes.ctl, "%s.%s" % (self.nodes.curves[c].shape, self.name))
            maya.cmds.parent(c, self.nodes.group)
            try:
                maya.cmds.rebuildCurve(c, s=self.maxDiv)
                maya.cmds.connectAttr("%s.worldSpace[0]" % self.nodes.curves[c].shape, "%s.inputCurve[%s]" % (self.nodes.loft, self.nodes.curves[c].id))
            except:
                continue
                
                
        maya.cmds.setAttr("%s.v" % self.nodes.group, False)
        maya.cmds.setAttr("%s.frame" % self.nodes.ctl, frame)
        maya.cmds.setAttr("%s.count" % self.nodes.ctl, self.maxDiv)
        maya.cmds.refresh(su=False)
        
        maya.cmds.currentTime(frame)
        maya.cmds.select(self.nodes.ctl)

        if verbose or dryrun:
            das.pprint(self.nodes)
                


trail = Blaze(p="nParticleShape1", emit="emitter1")        
trail.build()
trail.draw()

#points = trail.getParticles(p=trail.p, start=1, end=24)

#curves = trail.makeCurves(points=points, emit=trail.emit)
