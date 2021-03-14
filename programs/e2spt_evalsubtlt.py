#!/usr/bin/env python
# Muyuan Chen 2020-05
from future import standard_library
standard_library.install_aliases()
from EMAN2 import *
import numpy as np
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt
from eman2_gui.emapplication import get_application, EMApp
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from EMAN2_utils import *
from eman2_gui.valslider import ValSlider, ValBox


def main():
	
	usage=" "
	parser = EMArgumentParser(usage=usage,version=EMANVERSION)
	parser.add_argument("--path", type=str,help="path", default=None)
	parser.add_argument("--loadali2d", type=str,help="previous 2d alignment", default=None)
	parser.add_argument("--loadali3d", type=str,help="previous 3d alignment", default=None)
	#parser.add_argument("--inplace", action="store_true", default=False ,help="overwrite input.")
	#parser.add_argument("--invert", action="store_true", default=False ,help="invert direction.")

	(options, args) = parser.parse_args()
	logid=E2init(sys.argv)

	app = EMApp()
	win=EMSptEval(app, options)
	win.show()
	app.execute()
	
	E2end(logid)
	
## read aliptcls list and update info2d
def read_aliptcls(name, info):
	lst=LSXFile(name, True)
	xfkey=["type","alt","az","phi","tx","ty","tz","alpha","scale"]

	data={}
	for i in range(lst.n):
		l=lst.read(i)
		d=eval(l[2])

		dxf=Transform({k:d[k] for k in d.keys() if k in xfkey})
		k="{}-{}".format(l[1],l[0])
		data[k]=(dxf, d["score"])
	
	for i,d in enumerate(info):
		k="{}-{}".format(d["src"],d["idx"])
		d["pastxf"]=data[k][0]
		d["score"]=data[k][1]
		
	return info


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None):
        fig = Figure(figsize=(4, 4))
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        
        a=np.random.randn(1000,2)
        self.axes.plot(a[:,0], a[:,1],'.')


class EMSptEval(QtWidgets.QMainWindow):

	def __init__(self,application,options):
		QtWidgets.QWidget.__init__(self)
		
		self.options=options
		self.load_json()
		
		self.setMinimumSize(700,200)
		self.setCentralWidget(QtWidgets.QWidget())
		self.gbl = QtWidgets.QGridLayout(self.centralWidget())
		self.gbl.setColumnStretch( 2, 10 ) 
		
		self.imglst=QtWidgets.QTableWidget(1, 1, self)
		self.imglst.setMinimumSize(450, 100)
		self.gbl.addWidget(self.imglst, 0,1,10,1)
		self.imglst.cellClicked[int, int].connect(self.on_list_selected)
		

		self.update_list()
		
		#self.tiltid = ValSlider(rng=(0,1),label="Tilt_ID",value=0, rounding=0)
		#self.gbl.addWidget(self.tiltid,0,2,1,2)
		#self.tiltid.valueChanged.connect(self.event_tiltid)
		
		
		self.plotwinx=MplCanvas(self)
		#self.plotwinx.setMinimumSize(500, 100)
		self.plotx=self.plotwinx.axes
		self.plotx2=self.plotx.twinx()
		self.gbl.addWidget(self.plotwinx, 1,2,1,2)
		self.plotwinx.mpl_connect('button_press_event', self.onclick_plotx)
	
		self.plotwiny=MplCanvas(self)
		self.plotwiny.setMinimumSize(500, 500)
		self.ploty=self.plotwiny.axes
		self.gbl.addWidget(self.plotwiny, 2,2,7,2)
		
		self.cursel=-1
		
		
	def load_json(self):
		path=self.options.path
		print("Gathering metadata...")
		self.info3d=load_lst_params(f"{path}/particle_info_3d.lst")
		self.info2d=load_lst_params(f"{path}/particle_info_2d.lst")
		
		alipm=load_lst_params(self.options.loadali2d)
		for i,a in zip(self.info2d, alipm):
			i["pastxf"]=a["xform.projection"]
			i["score"]=a["score"]
			
		alipm=load_lst_params(self.options.loadali3d)
		for i,a in zip(self.info3d, alipm):
			i["xform.align3d"]=a["xform.align3d"]
			i["score"]=a["score"]
		
		#self.info2d=read_aliptcls(aliptcls, self.info2d)
		self.filenames, self.ptclcount=np.unique([d["src"] for d in self.info3d], return_counts=True)
		
		print("load {} particles from {} tomograms".format(len(self.info3d), len(self.filenames)))
		
	def on_list_selected(self, row, col):
		self.cursel=int(self.imglst.item(row, 0).text())
		fname=self.filenames[self.cursel]
		d3d=[d for d in self.info3d if d["src"]==fname]
		f=fname.replace("particles3d", "particles")
		tid=np.array([d["tilt_id"] for d in self.info2d if d["src"]==f])
		tid=np.sort(np.unique(tid))
		print("Loading {} particles from {} tilts...".format(len(d3d), len(tid)))
		#self.tiltid.setRange(np.min(tid), np.max(tid))
		#self.tiltid.setValue(int(np.mean(tid)), quiet=1)
		
		coord=np.array([d["coord"] for d in d3d])
		txfs=[d["xform.align3d"].inverse() for d in d3d]
		coord-=np.array([t.get_trans() for t in txfs])
		
		self.sel_coord=coord
		self.sel_score=[]
		self.sel_dxy=[]
		self.tltang=[]
		for td in tid:
		
			d3d=[d for d in self.info3d if d["src"]==fname]
			d2d=[]
			for d3 in d3d:
				d2=[self.info2d[d] for d in d3["idx2d"]]
				d2=[d for d in d2 if d["tilt_id"]==td]
				if len(d2)==0: continue
				d2d.append(d2[0])

			xfali=[d["pastxf"] for d in d2d]
			
			xfpj=[d["xform.projection"] for d in d2d]
			self.tltang.append(np.mean([x.get_params("xyz")["ytilt"] for x in xfpj]))
			xfraw=[a*b for a,b in zip(xfpj, txfs)]
			

			pastxf=([b*a.inverse()for a,b in zip(xfraw, xfali)])
			dxy=np.array([a.get_trans() for a in pastxf])
			score=[d["score"] for d in d2d]
			
			self.sel_score.append(score)
			self.sel_dxy.append(dxy)
		
		self.plt_scr=[np.mean(s) for s in self.sel_score]
		self.plt_dxy=[np.mean(np.linalg.norm(d, axis=1)) for d in self.sel_dxy]
		self.sel_tid=int(np.mean(tid))
		self.tltang=np.array(self.tltang)
		self.check_orient()
		
	def event_tiltid(self):
		if self.cursel>=0:
			self.check_orient()

	def onclick_plotx(self,event):
		if self.cursel>=0:
			self.sel_tid=np.argmin(abs(self.tltang-event.xdata))
			#p=int(np.round(event.xdata))
			#print(event.xdata,self.sel_tid)
			#self.sel_tid=p
			
			self.check_orient()
		
	def check_orient(self):
		
		#tid=int(self.tiltid.getValue())
		tid=self.sel_tid
		coord=self.sel_coord
		dxy=self.sel_dxy[tid]
		score=self.sel_score[tid]

		plot=self.ploty
		plot.cla()
		plot.quiver(coord[:,0], coord[:,1], dxy[:,0], dxy[:,1], score,  scale=100,width=.005,cmap='coolwarm')
				
		plot.axis('square');
		self.plotwiny.draw()
		
		
		plot=self.plotx
		plot.cla()
		plot.plot(self.tltang, self.plt_scr,'b')
		ax=self.plotx2
		ax.cla()
		ax.plot(self.tltang, self.plt_dxy,'--r')
		plot.vlines(self.tltang[tid], np.min(self.plt_scr), np.max(self.plt_scr))
		
		self.plotwinx.draw()
		
		
	def update_list(self):
		#### update file list
		files=self.filenames
		self.imglst.clear()
		self.imglst.setRowCount(len(files))
		self.imglst.setColumnCount(3)
		self.imglst.setHorizontalHeaderLabels(["ID", "FileName", "Ptcls"])
		self.imglst.setColumnHidden(0, True)
		for i,fname in enumerate(files):
			#### use Qt.EditRole so we can sort them as numbers instead of strings
			it=QtWidgets.QTableWidgetItem()
			it.setData(Qt.EditRole, i)
			self.imglst.setItem(i,0,it)
			
			self.imglst.setItem(i,1,QtWidgets.QTableWidgetItem(fname))
			
			c=self.ptclcount[i]
			self.imglst.setItem(i,2,QtWidgets.QTableWidgetItem(str(c)))
			
			
		for i,w in enumerate([50,300]):
			self.imglst.setColumnWidth(i,w)
		#self.imglst.setVerticalHeaderLabels([str(i) for i in range(len(self.imginfo))])
	
	
if __name__ == '__main__':
	main()
	