import das
import bakeUtils
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
        clmp = maya.cmds.createNode("clamp",                n="%s_clamp" % self.name)

        maya.cmds.addAttr(curv, ln="frame", at="float", min = self.frange[0], max = self.frange[1], k=True)
        maya.cmds.addAttr(curv, ln="spanType", at="enum", en="frame:uniform:", k=True)
        maya.cmds.addAttr(curv, ln="count", at="long", min=3, k=True)

        maya.cmds.connectAttr("%s.outputCurve" % cfos, "%s.inputCurve" % rebu )
        maya.cmds.connectAttr("%s.outputCurve" % rebu, "%s.create" % curv )
        maya.cmds.connectAttr("%s.outputSurface" % loft, "%s.create" % surf )
        maya.cmds.connectAttr("%s.outputSurface" % loft, "%s.inputSurface" % cfos )
        maya.cmds.connectAttr("%s.spanType" % curv, "%s.selector" % choi )
        maya.cmds.connectAttr("%s.frame" % curv, "%s.input1" % mins)
        maya.cmds.connectAttr("%s.output" % mins, "%s.isoparmValue" % cfos)
        maya.cmds.connectAttr("%s.output" % mins, "%s.inputR" % clmp)
        maya.cmds.connectAttr("%s.outputR" % clmp, "%s.input[0]" % choi)
        maya.cmds.connectAttr("%s.count" % curv, "%s.input[1]" % choi)
        maya.cmds.connectAttr("%s.output" % choi, "%s.spans" % rebu)

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
                    "surface" : surf,
                    "loft" : loft,
                    "curveFromSurface" : cfos}

        for node in nodes:
            self.nodes[node] = nodes[node]
 

    def draw(self, verbose=False, dryrun=False):
        frame = maya.cmds.currentTime(q=True)
        cid=0
        prepend = []
        for i in range(int(self.frange[0]), int(self.frange[1]+1)):
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
            
        for c in self.nodes.curves:
            maya.cmds.rebuildCurve(c, s=self.maxDiv)
            id = self.nodes.curves[c].id
            shape = self.nodes.curves[c].shape
            maya.cmds.connectAttr("%s.worldSpace[0]" % shape, "%s.inputCurve[%s]" % (self.nodes.loft, id))

        maya.cmds.setAttr("%s.v" % self.nodes.group, False)
        maya.cmds.setAttr("%s.frame" % self.nodes.curve, frame)
        maya.cmds.refresh(su=False)
        
        maya.cmds.currentTime(frame)
        maya.cmds.select(self.nodes.curve)

        if verbose or dryrun:
            das.pprint(self.nodes)

trail = Blaze(p="nParticleShape1", emit="emitter1")
trail.build()
trail.draw()

maya.cmds.getAttr("emitter1.t", time=(0))[0]