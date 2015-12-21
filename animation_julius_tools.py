# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

#Special thanks to khuuyj (https://sites.google.com/site/khuuyjblend/home/blender/script/lipsync)
#for his initial work on combining Blender and Julius.  Without his work, I would have nothing to re-arrange
#into a BGE compatible solution.

#If you would like to share where/what your using this, I'd love to hear it- drop me a line (dhall5@gmail.com)

bl_info = {
    "name": "Julius Tools",
    "description": "Receives data from Julius for real time shape key manipulation in both BPY and BGE. ",
    "author": "khuuyj, Dan Hall",
    "version": (2, 1),
    "blender": (2, 72, 0),
    "location": "View3D > UI",
    "category": "Animation",
    'wiki_url': '',
    'tracker_url': ''
    }

from types import *

import os
import re
from xml.dom import minidom

import time
import socket

import subprocess
from subprocess import *

try:
    import bge
    from bge import logic as logic
    GE = True
except ImportError:
    GE = False
    import bpy
    from bpy import *

 
    
if not GE:
    class JulipSyncReceiverLogicCreate(bpy.types.Operator):
        bl_idname = "wm.julipsync_receiver_logic_create"
        bl_label = "Create game logic"
        bl_description = "Create or update game logic for Julius receiver for the selected object"
        bl_options = {'REGISTER'}

        @classmethod
        def poll(self, context):
            return context.object != None
        
        def execute(self, context):
            ob = context.object
            prop = ob.jlipsync
            if 'SJulipSyncReceiver' not in ob.game.sensors:
                bpy.ops.logic.sensor_add(name='SJulipSyncReceiver')
            ob.game.sensors['SJulipSyncReceiver'].use_pulse_true_level = True
            
            if 'CJulipSyncReceiver' not in ob.game.controllers:
                bpy.ops.logic.controller_add(name='CJulipSyncReceiver', type='PYTHON')
            if 'AJulipSyncReceiver' not in ob.game.actuators:
                bpy.ops.logic.actuator_add(name='AJulipSyncReceiver', type='ACTION')
                
            ob.game.controllers['CJulipSyncReceiver'].mode = 'MODULE'
            ob.game.controllers['CJulipSyncReceiver'].module = 'animation_julius_tools.updateGE'
            ob.game.controllers['CJulipSyncReceiver'].link(ob.game.sensors['SJulipSyncReceiver'],ob.game.actuators['AJulipSyncReceiver'])
            
            
            if 'JulipIPAddress' not in ob.game.properties:
                bpy.ops.object.game_property_new(type='STRING', name='JulipIPAddress')
            ob.game.properties['JulipIPAddress'].type = 'STRING'
            ob.game.properties['JulipIPAddress'].value = prop.addr
            
            if 'JulipSyncPort' not in ob.game.properties:
                bpy.ops.object.game_property_new(type='STRING', name='JulipSyncPort')
            ob.game.properties['JulipSyncPort'].type = 'STRING'
            ob.game.properties['JulipSyncPort'].value = str(prop.port)
            
            if 'JulipLevel' not in ob.game.properties:
                bpy.ops.object.game_property_new(type='FLOAT', name='JulipLevel')
            ob.game.properties['JulipLevel'].type = 'FLOAT'
            ob.game.properties['JulipLevel'].value = prop.level
            
            if 'JulipMaxLevel' not in ob.game.properties:
                bpy.ops.object.game_property_new(type='FLOAT', name='JulipMaxLevel')
            ob.game.properties['JulipMaxLevel'].type = 'FLOAT'
            ob.game.properties['JulipMaxLevel'].value = prop.max_lev
            
            if 'JulipLowerLevel' not in ob.game.properties:
                bpy.ops.object.game_property_new(type='FLOAT', name='JulipLowerLevel')
            ob.game.properties['JulipLowerLevel'].type = 'FLOAT'
            ob.game.properties['JulipLowerLevel'].value = prop.lower_lev
            
            if 'JulipUpperLevel' not in ob.game.properties:
                bpy.ops.object.game_property_new(type='FLOAT', name='JulipUpperLevel')
            ob.game.properties['JulipUpperLevel'].type = 'FLOAT'
            ob.game.properties['JulipUpperLevel'].value = prop.upper_lev
            
            if 'JulipDump' not in ob.game.properties:
                bpy.ops.object.game_property_new(type='FLOAT', name='JulipDump')
            ob.game.properties['JulipDump'].type = 'FLOAT'
            ob.game.properties['JulipDump'].value = prop.dump

            if 'JulipFrameEnd' not in ob.game.properties:
                bpy.ops.object.game_property_new(type='INT', name='JulipFrameEnd')
            ob.game.properties['JulipFrameEnd'].type = 'INT'
            ob.game.properties['JulipFrameEnd'].value = bpy.context.scene.frame_end
            
            phoneme=split_str_into_len(str(phonemeToDictKey(prop.rel)),127)
            i=0
            for s in phoneme:
                if 'JulipPhonemeKeys_' + str(i)  not in ob.game.properties:
                    bpy.ops.object.game_property_new(type='STRING', name='JulipPhonemeKeys_'+str(i))
                ob.game.properties['JulipPhonemeKeys_'+str(i)].type = 'STRING'
                ob.game.properties['JulipPhonemeKeys_'+str(i)].value = s
                i+=1
            
            return {'FINISHED'}
 
 
    ###################################################################
    #   Properties : bpy.types.Object.jlipsync
    ###################################################################
    class phoneme_prop(bpy.types.PropertyGroup):
        key = bpy.props.StringProperty(name="Key",default="")

    class keyrelation(bpy.types.PropertyGroup):
        phoneme = bpy.props.StringProperty(name="phoneme",default="",maxlen=5)
        include_long = bpy.props.BoolProperty(name="Include Long",default=True)
        shapekey = bpy.props.IntProperty(name="ShapeKey",default=0)

    class lipsync_props(bpy.types.PropertyGroup):
        # For Thread Control
        connect = bpy.props.BoolProperty(name="Connect",default=False)
        pause = bpy.props.BoolProperty(name="Pause",default=False)
        phoneme = bpy.props.BoolProperty(name="Phoneme",default=False)
        setting = bpy.props.BoolProperty(name="Setting",default=False)
        
        #Keys view
        level = bpy.props.FloatProperty(name="Level",default=0,precision=3,subtype="FACTOR",min=0,max=1.0)
        max_lev = bpy.props.FloatProperty(name="Max Level",default=32768,min=0,max=65536)
        upper_lev = bpy.props.FloatProperty(name="Upper Level",default=1,precision=3,subtype="FACTOR",min=0,max=1)
        lower_lev = bpy.props.FloatProperty(name="Lower Level",default=0,precision=3,subtype="FACTOR",min=0,max=1)
        #pow_lev = bpy.props.FloatProperty(name="Power",default=1,min=1,max=100)
        dump = bpy.props.FloatProperty(name="Dump",default=0,precision=3,subtype="FACTOR",min=0,max=1)
        rel = bpy.props.CollectionProperty(type=keyrelation)
        recog = bpy.props.StringProperty(name="Recog",default="")
        
        #Setting
        addr = bpy.props.StringProperty(name="addr",default="127.0.0.1")
        port = bpy.props.IntProperty(name="ip",default=10500)
        autorun = bpy.props.BoolProperty(name="AutoRun julius",default=False)
        modpath = bpy.props.StringProperty(name="Module Path",default="/",subtype="FILE_PATH")
        jcopath = bpy.props.StringProperty(name="Config Path",default="/",subtype="FILE_PATH")
        charconv = bpy.props.StringProperty(name="Dictionary Code Type",default="utf-8")
    #wavpath = bpy.props.StringProperty(name="Wave Path",default="mic",subtype="FILE_PATH")
    ###################################################################
    #   jthread : modal timer operator
    ###################################################################
    class lipsync_timer(bpy.types.Operator):
        bl_idname = "wm.lipsync_timer"
        bl_label = "Lipsync Timer"

        __p = None
        __obj = None
        __timer = None
        __dict = {}
        __frame = None    
        __rec = ""

        @classmethod
        def poll(cls,context):
            if context==None:
                pass
            elif context.object==None:
                pass
            elif context.object.jlipsync.connect:
                pass
            else:
                return 1
            return 0
            
        def cancel(self,context):
            try:
                self.report({"INFO"},"Disconnect from julius")
            except Exception as e:
                self.report({"ERROR"},"%s" %(e))
            if type(self.__p)!=None:
                try:
                    self.__p.terminate()
                    self.__p.wait()
                    self.__p = None
                except Exception as e:
                    pass
                    #self.report({"ERROR"},"%s" %(e))
                    
            context.window_manager.event_timer_remove(self.__timer)
            #self.__obj.jlipsync.connect = False            
            del self.receiver

            return {'CANCELLED'}
        
        

        def modal(self,context,event):
            if event.type=="ESC":
                #return self.cancel(context)
                pass
            elif event.type=="TIMER":
                self.receiver.run()
            return {'PASS_THROUGH'}

        def execute(self,context):
            self.__obj = context.object
            prop = self.__obj.jlipsync
            
			
            # Start Server
            if self.start_server(prop):
                pass
            else:
                return {'FINISHED'}
            frame_end=bpy.context.scene.frame_end
            self.receiver = JulipSyncReceiver(prop.addr,prop.port,prop.level,prop.max_lev,prop.lower_lev,prop.upper_lev,prop.dump,False,frame_end,context.object)
            self.receiver.dict_key=phonemeToDictKey(prop.rel)
            
            if type(self.receiver.sock)!=None:
                t = 1/context.scene.render.fps
                context.window_manager.modal_handler_add(self)
                self.__timer = context.window_manager.event_timer_add(t,context.window)
                prop.connect = True
                prop.pause = True
                return {'RUNNING_MODAL'}
            else:
                try:
                    self.receiver = None
                except:
                    pass
                return {'FINISHED'}

        def remove_escape_seq(self,str):
            w = ""
            a = str.replace("\\","/")
            for i in range(len(a)):
                if a[i:i+1]=="\a":
                    w += "/a"
                elif a[i:i+1]=="\b":
                    w += "/b"
                elif a[i:i+1]=="\f":
                    w += "/f"
                elif a[i:i+1]=="\r":
                    w += "/r"
                elif a[i:i+1]=="\t":
                    w += "/t"
                elif a[i:i+1]=="\v":
                    w += "/v"
                else:
                    w += a[i:i+1]
            if w.startswith("//../"):
                w = "./" + w[5:]
                w = os.path.abspath(w)
            #print(w)
            return w
        
        def start_server(self,prop):
            if prop.autorun:
                modpath = self.remove_escape_seq(prop.modpath)
                jcopath = self.remove_escape_seq(prop.jcopath)
                if modpath[0:2]=="//" : modpath = modpath[2:]
                if jcopath[0:2]=="//" : jcopath = jcopath[2:]
                #wavpath = self.remove_escape_seq(prop.wavpath)    
                if modpath and jcopath:
                    #if os.path.isfile(wavpath):
                    #    indev = wavpath
                    #else:
                    #    indev = "mic"
                    #commandline = prop.modpath + " -input " + indev + " -C " + prop.jcopath + " -charconv " + prop.charconv + " utf-8 -progout -outcode wlpsWLPSCR -module " + str(prop.port)
                    commandline = modpath + " -input mic -C " + jcopath + " -charconv " + prop.charconv + " utf-8 -outcode wlpsWLPSCR -module " + str(prop.port)
                    self.report({"INFO"},commandline)
                    try:
                        self.__p = Popen(commandline.split(" "),bufsize=8192)
    #                    if os.name=="nt":
    #                        self.__p = Popen(commandline.split(" "),bufsize=8192)
    #                    else:
    #                        self.__p = Popen(commandline.split(" "),bufsize=8192,stdin=PIPE,stdout=PIPE,close_fds=True)
                        time.sleep(5)
                    except Exception as e:
                        self.report({'ERROR'},e)
                        self.report({'ERROR'},"Failure to start julius server!")
                        return False
                else:
                    self.report({"ERROR"},"julius can't be started by failure path")
                    return False
            else:
                pass
            return True
             
                    
    ###################################################################
    #   UI Operator
    ###################################################################
    def draw_callback(context):
        if context==None:
            pass
        elif context.object==None:
            pass
        elif context.object.type=="MESH":
            
            obj = context.object
            prop = obj.jlipsync
            if len(prop.rel)<len(obj.data.shape_keys.key_blocks):
                while len(prop.rel)<len(obj.data.shape_keys.key_blocks):
                    prop.rel.add()
            else:
                while len(prop.rel)>len(obj.data.shape_keys.key_blocks):
                    p = prop.rel[len(prop.rel)-1]
                    prop.list.remove(p)
        
    class ANIM_OT_jlipconnect(bpy.types.Operator):
        bl_idname="anim.jlipconnect"
        bl_label="Connect Voice Server"
        
        @classmethod
        def poll(cls,context):
            if context==None:
                pass
            elif context.object==None:
                pass
            elif context.object.jlipsync.connect:
                pass
            else:
                return 1
            return 0

        def execute(self,context):
            self.report({"INFO"},"Start capture")
            return bpy.ops.wm.lipsync_timer()

    class ANIM_OT_jlipdisconnect(bpy.types.Operator):
        bl_idname="anim.jlipdisconnect"
        bl_label="Disconnect Voice Server"

        @classmethod
        def poll(cls,context):
            if context==None:
                pass
            elif context.object==None:
                pass
            elif context.object.jlipsync.connect:
                return 1
            return 0

        def execute(self,context):
            context.object.jlipsync.connect = False
        
            return {'FINISHED'}
        
        
    class ANIM_OT_jlipstart(bpy.types.Operator):
        bl_idname="anim.jlipstart"
        bl_label="Start capture"
        
        @classmethod
        def poll(cls,context):
            if context==None:
                pass
            elif context.object==None:
                pass
            elif context.object.jlipsync.connect:
                if context.object.jlipsync.pause==True:
                    return 1
            return 0
        
        def execute(self,context):
            context.object.jlipsync.pause = False
            return {'FINISHED'}
        
    class ANIM_OT_jlipstop(bpy.types.Operator):
        bl_idname="anim.jlipstop"
        bl_label="Stop capture"
        
        @classmethod
        def poll(cls,context):
            if context.object==None:
                pass
            elif context.object.jlipsync.connect:
                if context.object.jlipsync.pause==False:
                    return 1
            return 0

        def execute(self,context):
            context.object.jlipsync.pause = True
            return {'FINISHED'}
        
    class ANIM_OT_jlipkeyadd(bpy.types.Operator):
        bl_idname="anim.jlipkeyadd"
        bl_label="Add Keys"
        
        def execute(self,context):
            context.object.jlipsync.rel.add()
            return {'FINISHED'}
    
    ###################################################################
    #   UI
    ###################################################################
    class ANIM_PT_jlipsync(bpy.types.Panel):
        bl_idname="anim.jlipsync"
        bl_label="Lip Sync"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_context = 'data'

        __handle = None

        @classmethod
        def poll(cls,context):
            if context==None:
                pass
            elif context.object==None:
                pass
            elif context.object.type=="MESH":
                if context.object.data.shape_keys==None:
                    pass
                elif len(context.object.data.shape_keys.key_blocks)>1:
                    return 1
            return 0
        
        def draw(self,context):
            if context==None:
                pass
            elif context.object==None:
                pass
            else:
                if ANIM_PT_jlipsync.__handle==None:
                    ANIM_PT_jlipsync.__handle = context.region.callback_add(draw_callback,(context,),'POST_PIXEL')
                    pass

                obj = context.object
                prop = obj.jlipsync
     
                layout = self.layout
                box0= layout.box()
                row0 = box0.row(align=True)
                row0.operator(lipsync_timer.bl_idname,text="Connect")
                row0.operator(ANIM_OT_jlipdisconnect.bl_idname,text="Disconnect")
                row0.operator(ANIM_OT_jlipstart.bl_idname,text="",icon="REC")
                row0.operator(ANIM_OT_jlipstop.bl_idname,text="",icon="PAUSE")
                row1 = box0.row(align=True)
                row1.prop(prop,"phoneme",text="Show Keys")
                row1.prop(prop,"setting",text="Setting")
                if prop.phoneme:
                    box1 = layout.box()
                    col0 = box1.column(align=True)
                    col0.prop(prop,"level",text="Level")
                    col0.prop(prop,"lower_lev",text="Lower Threshold")
                    col0.prop(prop,"upper_lev",text="Upper Threshold")
                    col0.prop(prop,"dump",text="Dump")
                    #col0.prop(prop,"pow_lev",text="Power")
                    col1 = box1.column()
                    row = []
                    i=0
                    k=0
                    for s in obj.data.shape_keys.key_blocks:
                        if i>0:
                            if i<len(prop.rel):
                                row.append(col1.row(align=True))
                                #row[k].prop(prop.rel[i],"phoneme",text="")
                                row[k].prop_search(prop.rel[i],"phoneme",context.scene,"phonemes",text="")
                                row[k].prop(prop.rel[i],"include_long",text="")
                                row[k].prop(s,"value",text=s.name)
                            k+=1
                        i+=1
                    col1.prop(prop,"recog",text="Recog")
                if prop.setting:
                    box2 = layout.box()
                    col2 = box2.column(align=False)
                    col2.label(text="julius Server Location")
                    col2.prop(prop,"addr",text="IP Address")
                    row2 = col2.row(align=True)
                    row2.label(text="Port")
                    row2.prop(prop,"port",text="")
                    row3 = col2.row(align=True)
                    row3.prop(prop,"autorun")
                    if prop.autorun==True:
                        row4 = col2.row(align=True)
                        row5 = col2.row(align=True)
                        row6 = col2.row(align=True)
                        row7 = col2.row(align=True)
                        row4.prop(prop,"modpath",text="julius Path")
                        row5.prop(prop,"jcopath",text="jconf Path")
                        row6.prop(prop,"charconv",text="Encode")
                       # row7.prop(prop,"wavpath",text="Input")


					   
    class ANIM_PT_jlipsync_GE(bpy.types.Panel):
        bl_idname="anim.jlipsync_ge"
        bl_label="GE Lip Sync"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_context = 'data'
        __handle = None

        @classmethod
        def poll(cls,context):
            if context==None:
                pass
            elif context.object==None:
                pass
            elif context.object.type=="MESH":
                if context.object.data.shape_keys==None:
                    pass
                elif len(context.object.data.shape_keys.key_blocks)>1:
                    return 1
            return 0
			
			
        def draw(self,context):
            layout = self.layout
            scene = context.scene
            col = layout.column()
            if context.object != None and "CJulipSyncReceiver" in context.object.game.controllers:
                col.operator("wm.julipsync_receiver_logic_create", icon='FILE_REFRESH', text="Update game logic")
            else:
                col.operator("wm.julipsync_receiver_logic_create", icon='GAME')

          
    def register():    
        bpy.utils.register_module(__name__)
        bpy.types.Object.jlipsync = bpy.props.PointerProperty(type=lipsync_props,
                                                      options={'HIDDEN'})
        bpy.types.Scene.phonemes = bpy.props.CollectionProperty(type=phoneme_prop,
                                                      options={'HIDDEN'})
    def unregister():
        bpy.utils.unregister_module(__name__)

        
    if __name__ == "__main__":
        register()    

#NImateReceiver(port, quit_port, message_port, profile_path)
class JulipSyncReceiver():
    sock = None
    obj = None
    level=None
    max_level=None
    lower_level=None
    upper_level=None
    dump=None
    pause=None
    frame_end=0
    dict_key={}
    action_length=0
    sounds_list=None
    
    __rec = ""
	
	
    def run(self):
        if self.sock==None:
            pass
        else:
            global GE
            #prop = self.obj.jlipsync
            #self.dict_key={}
            dict_val={}
            i = 0
            #for p in self.relation:
            #    if p.phoneme!="":
            #        self.dict_key.update({p.phoneme:i})
            #        if p.include_long:
            #            p1 = p.phoneme + ":"
            #            self.dict_key.update({p1:i})
            #    i += 1
            
            for i in self.dict_key:
                dict_val.update({self.dict_key[i]:0.0})
            # Pick phoneme & sum score
            lv0 = 0
            v = 0.0
            v1 = 10000000.0
            v2 = 0.0
            i1 = 0.0
            i2 = 0.0
            r = 0.0
            min_v = 1000.0
            max_v = -1000.0
            vsum = 0.0
            doc = self.recieve()
            for d in doc:
                #for r in d.getElementsByTagName("RECOGOUT"):
                #    for sy in r.getElementsByTagName("SHYPO"):
                #        rk = sy.getAttribute("RANK")
                #        if rk=="1":
                #            txt = ""
                #            for t in sy.getElementsByTagName("WHYPO"):
                #                w = t.getAttribute("WORD")
                #                if w==None:
                #                    pass
                #                elif w in ("<s>","</s>","sp","sil"):
                #                    pass
                #                elif txt=="":
                #                    txt = w
                #                else:
                #                    txt = txt + " " + w
                #            #prop.recog = txt
                for n in d.getElementsByTagName("PHONEME"):
                    l = n.getAttribute("LEV")
                    if l==None:
                        pass
                    elif l.isdigit():
                        if int(l)>lv0:
                            lv0 = int(l)
                    pm = n.getAttribute("PHONE")
                    for p in n.getElementsByTagName("STATE"):
                        ph = p.getAttribute("PHONE")
                        sc = p.getAttribute("SCORE")

                        if ph==None or sc==None:
                            pass
                        else:
                            #print(ph,sc)
                            i = ph.find("-")
                            if i>=0: ph = ph[i+1:]
                            i = ph.find("+")
                            if i>0: ph = ph[:i-1]

                            i = self.dict_key.get(ph)
                            if i==None:
                                if  not GE:
                                    if bpy.context.scene.phonemes.get(ph)==None:
                                        lp = bpy.context.scene.phonemes.add()
                                        lp.name = ph
                                        lp = ph
                                #else:
                                #    if self.dict_key.get(ph)==None:
                                #        lp = self.dict_key.update({ph:0})
                                #        lp.name = ph
                                #        lp = ph
                                        
                            else:
                                v0 = (100 + float(sc))/100;
                                if v0<min_v:min_v=v0
                                if v0>max_v:max_v=v0
                                #v0 = v0 ** prop.pow_lev
                                v = dict_val.get(i)
                                if v==None:
                                    dict_val.update({i:v0})
                                elif v<v0:
                                    dict_val.update({i:v0})
                                #print(ph,v,v0)

            # Get min & max
            self.level = lv0/self.max_level
            for i in dict_val:
                if not GE:
                    s = self.obj.data.shape_keys.key_blocks[i]
                    v = dict_val[i] * self.level
                    v = max(0.0,(v - self.lower_level))
                    v = v / (self.upper_level - self.lower_level)
                    if self.dump > 0:
                     v3 = s.value - v
                     if v3 > 0:
                         v = s.value - v3 * (1 - self.dump)
                    if self.pause:
                     pass
                    else:
                     rt = self.keyframe_insert(self.obj.data.shape_keys,bpy.context.scene.frame_current,s,v)
                    s.value = v
                    #            print(st)
                else:
                    
                    controller = logic.getCurrentController()
                    actuator = controller.owner.actuators["AJulipSyncReceiver"]
    
                    
                    v = dict_val[i] * self.level
                    v = max(0.0,(v - self.lower_level))
                    v = v / (self.upper_level - self.lower_level)
                    frame_end=self.frame_end
                    #percent = v
                    
                    
                    if self.sounds_list==None:
                        self.sounds_list=list(self.dict_key.keys())
                    if self.action_length==0:
                        self.action_length=int((frame_end)/len(self.dict_key))
                    if v>self.dump:
                        #name = actuator.action
                        #layer = actuator.layer
                        #priority = int(100-(percent*100))
                        #blendin = actuator.frame_blend_in
                        #mode = bge.logic.KX_ACTION_MODE_PLAY
                        #layerWeight =actuator.layer_weight
                        #ipoFlags = 1
                        #speed = 1.0
                        #self.obj.playAction(name,start, end, layer, priority, blendin, mode, layerWeight, ipoFlags, speed)
                        
                        start=self.dict_key[self.sounds_list[i-1]]*self.action_length-self.action_length
                        end = start +self.action_length
                        #start=0
                        #end =self.action_length
                        actuator.frameStart=start
                        actuator.frameEnd=end
                        actuator.priority=10-int(round(v))
                        controller.activate("AJulipSyncReceiver")
                

    def recieve(self):
        ret = []
        rec = []

        try:
            recv = self.sock.recv(4098)
        except socket.error as e:
            if e.errno==11 or e.errno==10035:
                recv = b''
            else:
                #self.report({"ERROR"},"!ERROR! Failure to recieve:%s" %(e))
                print("!ERROR! Failure to receive:%s" %(e))
                return None

        try:
            recv = recv.decode("utf-8")
        except Exception as e:
            print("!WARN! Failure to encode:%s" %(e))
            recv = ""

        recv = re.sub("\<s\>", "&lt;s&gt;", recv)
        recv = re.sub("\</s\>", "&lt;/s&gt;", recv)
        self.__rec = self.__rec + recv
        r = self.__rec.split(".\n")
        i = 0
        for rec in r:
            if rec.find("<PHONEME")>=0 or rec.find("<RECOGOUT")>=0:
                try:
                    d = minidom.parseString(rec)
                    ret.append(d)
                    if i==len(r)-1:
                        i+=1
                except Exception as e:
    #                    print("!ERROR! Failure to convert to xml",e)
    #                    print(rec)
                    pass
                if i<len(r)-1:
                    i+=1
        if i==len(r)==0:
            self.__rec = ""
        else:
            self.__rec = r[len(r)-1]

        return ret

    def keyframe_insert(self,shapekeys,fr,shape,value):
            if shape.name=="Basis": return True
            if shapekeys.animation_data==None:
                a = bpy.data.actions.new("KeyAction")
                shapekeys.animation_data_create()
                shapekeys.animation_data.action = a
            else:
                a = shapekeys.animation_data.action
            f = None
            path = "key_blocks[\"%s\"].value" %(shape.name)
            for f0 in a.fcurves:
                if f0.data_path==path:
                    f = f0
                    break
            if f==None: f = a.fcurves.new(path,0,"")
            f.keyframe_points.insert(fr,value)
            return True      		

    def __init__(self, ip,port,level,max,lower,upper,dump,pause,frame_end,obj):
        self.obj = obj
        self.level=level
        self.max_level=max
        self.lower_level=lower
        self.upper_level=upper
        self.dump=dump
        self.pause=pause
        self.frame_end=frame_end
        
        try:
            print({"INFO"},"Connect to julis/%s:%d" %(ip,port))
            addr = (ip,port)
            self.sock=socket.socket()
            self.sock.connect(addr)
            self.sock.setblocking(0)
            time.sleep(2)
        except Exception as e:
            self.sock = None
            print({"ERROR"},"Failure to connect!:%s" %(e))
        return None
        
    def __del__(self):
        self.sock.close()
        print("JulipSync stopped listening")


def phonemeToDictKey(relation):
    i = 0
    dict_key={}
    for p in relation:
        if p.phoneme!="":
            dict_key.update({p.phoneme:i})
            if p.include_long:
                p1 = p.phoneme + ":"
                dict_key.update({p1:i})
        i += 1
    return dict_key

def split_str_into_len(s, l=2):
    """ Split a string into chunks of length l """
    return [s[i:i+l] for i in range(0, len(s), l)]    

def updateGE(controller):
    import bge
    if hasattr(bge.logic, 'JulipSync') == False:
        setupGE(controller.owner)

    bge.logic.JulipSync.run()
    
def setupGE(own):
    import bge
    import sys

    address = own.get('JulipIPAddress', "")
    port = int(own.get('JulipSyncPort', ""))
    level = own.get('JulipLevel', "")
    max_level = own.get('JulipMaxLevel', "")
    lower_level = own.get('JulipLowerLevel', "")
    upper_level = own.get('JulipUpperLevel', "")
    dump = own.get('JulipDump', "")
    frame_end=own.get('JulipFrameEnd', "")
    i=0
    dict_key=""
    while own.get('JulipPhonemeKeys_'+str(i), False):
        dict_key = dict_key + own.get('JulipPhonemeKeys_'+str(i))
        i=i+1

    tmp_dict=eval(dict_key)
    d = dict((k,v) for k, v in tmp_dict.items() if k.find(':')==-1)


    bge.logic.JulipSync = JulipSyncReceiver(address, port, level, max_level, lower_level, upper_level, dump, False, frame_end, own)
    bge.logic.JulipSync.dict_key=d