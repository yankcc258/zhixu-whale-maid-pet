import numpy as np
def q2m(q):
    x,y,z,w=q; return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
def local(n):
    M=np.eye(4)
    if 'matrix' in n: return np.array(n['matrix']).reshape(4,4).T
    R=q2m(n.get('rotation',[0,0,0,1])); S=np.diag(n.get('scale',[1,1,1])); M[:3,:3]=R@S; M[:3,3]=n.get('translation',[0,0,0]); return M
def world(j,i):
    par={c:k for k,n in enumerate(j['nodes']) for c in n.get('children',[])}
    M=np.eye(4)
    while i is not None: M=local(j['nodes'][i])@M; i=par.get(i)
    return M
