"""Repository directory ownership, ordering and safe structural changes."""
import uuid
from models import RepositoryFolder as Folder,RepositoryFolderCase as Member,RepositoryFolderNode as Node,RepositoryCase
import plan_state as ps
ROOT='repository-bmc-root'

def siblings(s,parent):
 return s.query(Node).filter_by(parent_id=parent).order_by(Node.position,Node.folder_id).all()

def normalize(nodes):
 for i,node in enumerate(nodes):node.position=i

def ensure(s):
 if not s.get(Folder,ROOT):
  s.add(Folder(id=ROOT,name='BMC',normalized_name='@bmc-root'));s.flush()
 if not s.get(Node,ROOT):s.add(Node(folder_id=ROOT,parent_id=None,position=0));s.flush()
 for f in s.query(Folder).order_by(Folder.normalized_name):
  if not s.get(Node,f.id):
   s.add(Node(folder_id=f.id,parent_id=ROOT,position=len(siblings(s,ROOT))));s.flush()
 for case in s.query(RepositoryCase):
  if not s.get(Member,case.id):s.add(Member(repository_id=case.id,folder_id=ROOT))
 s.flush()

def path(s,identity):
 names=[];seen=set()
 while identity:
  if identity in seen:raise ps.StateError('Directory cycle detected',409)
  seen.add(identity);names.append(ps.require(s,Folder,identity).name);identity=ps.require(s,Node,identity).parent_id
 return list(reversed(names))

def subtree(s,identity):
 ps.require(s,Folder,identity);result=[];pending=[identity]
 while pending:
  node=pending.pop();result.append(node)
  pending.extend(n.folder_id for n in reversed(siblings(s,node)))
 return result

def records(s):
 return [dict(id=i,name=ps.require(s,Folder,i).name,parent_id=s.get(Node,i).parent_id,position=s.get(Node,i).position,folder_path='/'.join(path(s,i)),count=s.query(Member).filter_by(folder_id=i).count(),is_root=i==ROOT) for i in subtree(s,ROOT)]

def validate(s,name,parent,identity=None):
 if not isinstance(name,str) or not name.strip() or len(name.strip())>100 or any(c in name for c in '/\\'):
  raise ps.StateError('Enter a folder name of 1-100 characters without slashes.')
 ps.require(s,Folder,parent)
 if identity and parent in subtree(s,identity):raise ps.StateError('A folder cannot move into itself or its descendants.',409)
 if any(n.folder_id!=identity and s.get(Folder,n.folder_id).name.casefold()==name.strip().casefold() for n in siblings(s,parent)):
  raise ps.StateError('A sibling folder already has this name.',409)
 return name.strip()

def create(s,data):
 parent=data.get('parent_id') or ROOT;name=validate(s,data.get('name'),parent)
 identity=str(uuid.uuid4());f=Folder(id=identity,name=name,normalized_name='@'+identity)
 s.add(f);s.flush();s.add(Node(folder_id=identity,parent_id=parent,position=len(siblings(s,parent))));s.flush()
 return next(r for r in records(s) if r['id']==identity)

def change(s,identity,data):
 if identity==ROOT:raise ps.StateError('The BMC root cannot be edited or moved.',409)
 f=ps.require(s,Folder,identity);node=ps.require(s,Node,identity);old=node.parent_id;parent=data.get('parent_id',old)
 if not parent:raise ps.StateError('Folders must remain under BMC.')
 name=validate(s,data.get('name',f.name),parent,identity)
 destination=[n for n in siblings(s,parent) if n.folder_id!=identity]
 relative=data.get('relative_to');insertion=data.get('insertion')
 if relative or insertion:
  anchor=ps.require(s,Node,relative)
  if relative==identity or anchor.parent_id!=parent or insertion not in ('before','after'):raise ps.StateError('Choose a sibling and before/after insertion.')
  index=next(i for i,n in enumerate(destination) if n.folder_id==relative)+(insertion=='after')
 else:index=min(node.position,len(destination)) if parent==old else len(destination)
 f.name=name;node.parent_id=parent;destination.insert(index,node);normalize(destination);s.flush()
 if old!=parent:normalize(siblings(s,old))
 return next(r for r in records(s) if r['id']==identity)

def remove(s,identity,data):
 if identity==ROOT:raise ps.StateError('The BMC root cannot be removed.',409)
 node=ps.require(s,Node,identity);parent=node.parent_id;ids=subtree(s,identity)
 if data.get('confirm') is not True:raise ps.StateError('Confirm deletion of the directory and all its Test Cases.')
 case_ids=[m.repository_id for m in s.query(Member).filter(Member.folder_id.in_(ids))]
 s.query(Member).filter(Member.folder_id.in_(ids)).delete(synchronize_session=False)
 s.query(RepositoryCase).filter(RepositoryCase.id.in_(case_ids)).delete(synchronize_session=False)
 for i in reversed(ids):
  s.delete(ps.require(s,Node,i));s.flush();s.delete(ps.require(s,Folder,i));s.flush()
 normalize(siblings(s,parent));return dict(status='ok',parent_id=parent,removed_cases=len(case_ids),removed_folders=len(ids))


def batch(s,data):
 folders=data.get('folder_ids',[]);cases=data.get('case_ids',[])
 if not isinstance(folders,list) or not isinstance(cases,list) or any(not isinstance(i,str) for i in folders+cases) or not (folders or cases):raise ps.StateError('Select directories or Test Cases.')
 folders=list(dict.fromkeys(folders));cases=list(dict.fromkeys(cases))
 if ROOT in folders:raise ps.StateError('The BMC root cannot be selected for move/delete.',409)
 covered=set()
 for identity in folders:covered.update(subtree(s,identity))
 roots=[i for i in folders if ps.require(s,Node,i).parent_id not in covered]
 for i in cases:ps.require(s,RepositoryCase,i)
 direct=[i for i in cases if ps.require(s,Member,i).folder_id not in covered]
 action=data.get('action')
 if action=='delete':
  if data.get('confirm') is not True:raise ps.StateError('Confirm deletion of all selected directories and Test Cases.')
  count=0
  for identity in roots:count+=remove(s,identity,{'confirm':True})['removed_cases']
  for identity in direct:s.delete(ps.require(s,Member,identity));s.delete(ps.require(s,RepositoryCase,identity));count+=1
  return dict(status='ok',removed_cases=count,removed_folders=len(covered))
 if action=='move':
  target=data.get('folder_id');ps.require(s,Folder,target)
  if target in covered:raise ps.StateError('Cannot move a selection into its own directory tree.',409)
  for i in roots:validate(s,s.get(Folder,i).name,target,i)
  for i in roots:change(s,i,{'parent_id':target})
  for i in direct:s.get(Member,i).folder_id=target
  s.flush();return dict(status='ok',moved_folders=len(roots),moved_cases=len(direct))
 raise ps.StateError('Choose move or delete.')
