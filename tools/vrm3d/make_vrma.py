"""Minimal VRMA writer for testing: python3 make_vrma.py out.vrma"""
import json, struct, math, sys
import numpy as np
# T-pose-ish skeleton (metres), parent → children
B=[('hips',None,[0,0.78,0]),('spine',0,[0,0.1,0]),('chest',1,[0,0.12,0]),('neck',2,[0,0.2,0]),('head',3,[0,0.08,0]),
   ('leftUpperArm',2,[0.17,0.15,0]),('leftLowerArm',5,[0.24,0,0]),('leftHand',6,[0.22,0,0]),
   ('rightUpperArm',2,[-0.17,0.15,0]),('rightLowerArm',8,[-0.24,0,0]),('rightHand',9,[-0.22,0,0]),
   ('leftUpperLeg',0,[0.08,-0.04,0]),('leftLowerLeg',11,[0,-0.38,0]),('leftFoot',12,[0,-0.36,0]),
   ('rightUpperLeg',0,[-0.08,-0.04,0]),('rightLowerLeg',14,[0,-0.38,0]),('rightFoot',15,[0,-0.36,0])]
nodes=[]; 
for i,(n,p,t) in enumerate(B):
    nodes.append({'name':n,'translation':t})
for i,(n,p,t) in enumerate(B):
    if p is not None: nodes[p].setdefault('children',[]).append(i)
hb={n:{'node':i} for i,(n,p,t) in enumerate(B)}
# animation: 2 s, 30 fps: head nod (x), left upper arm raise (z), hips bob (y translation)
fps=30; T=2.0; N=int(T*fps)+1; times=np.linspace(0,T,N).astype(np.float32)
def q_axis(ax,deg):
    s=math.sin(math.radians(deg)/2); return [ax[0]*s,ax[1]*s,ax[2]*s,math.cos(math.radians(deg)/2)]
headq=np.array([q_axis([1,0,0],18*math.sin(2*math.pi*t/1.0)) for t in times],np.float32)
armq=np.array([q_axis([0,0,1],60*(0.5-0.5*math.cos(2*math.pi*t/2.0))) for t in times],np.float32)
hipsT=np.array([[0,0.78+0.03*math.sin(2*math.pi*t/0.5),0] for t in times],np.float32)
bufs=[]; views=[]; accs=[]
def add(arr,typ,comp=5126):
    arr=np.ascontiguousarray(arr); off=sum(len(b) for b in bufs); bufs.append(arr.tobytes()); 
    while sum(len(b) for b in bufs)%4: bufs.append(b'\0')
    views.append({'buffer':0,'byteOffset':off,'byteLength':arr.nbytes}); a={'bufferView':len(views)-1,'componentType':comp,'count':int(arr.shape[0]),'type':typ}
    if typ=='SCALAR': a['min']=[float(arr.min())]; a['max']=[float(arr.max())]
    accs.append(a); return len(accs)-1
ti=add(times,'SCALAR'); hq=add(headq,'VEC4'); aq=add(armq,'VEC4'); ht=add(hipsT,'VEC3')
anim={'name':'test','samplers':[{'input':ti,'output':hq,'interpolation':'LINEAR'},{'input':ti,'output':aq,'interpolation':'LINEAR'},{'input':ti,'output':ht,'interpolation':'LINEAR'}],
      'channels':[{'sampler':0,'target':{'node':4,'path':'rotation'}},{'sampler':1,'target':{'node':5,'path':'rotation'}},{'sampler':2,'target':{'node':0,'path':'translation'}}]}
BIN=b''.join(bufs)
j={'asset':{'version':'2.0','generator':'luna-vrma-test'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':nodes,'buffers':[{'byteLength':len(BIN)}],'bufferViews':views,'accessors':accs,'animations':[anim],
   'extensionsUsed':['VRMC_vrm_animation'],'extensions':{'VRMC_vrm_animation':{'specVersion':'1.0','humanoid':{'humanBones':hb}}}}
js=json.dumps(j,separators=(',',':')).encode(); 
while len(js)%4: js+=b' '
open(sys.argv[1],'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\0')+BIN)
print('wrote',sys.argv[1])
