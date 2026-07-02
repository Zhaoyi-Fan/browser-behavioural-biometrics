// Content script: listens for keyboard and mouse events on every page the
// user visits and forwards each one to the background script, which uploads it
// to the collection server. Injected into all pages by manifest.json.
//
// This is the data-collection artefact from the PhD (thesis Chapter 5),
// lightly cleaned for release: two original bugs are fixed (see keyDown and
// mousePosition) and the hard-coded collection server has been replaced with a
// placeholder. It is Manifest V2, which Chrome has since deprecated - kept as
// a faithful record of the tool used in the experiments, not for production
// use.
document.addEventListener("mousemove",mm);
document.addEventListener("mousedown",md);
document.addEventListener("mouseup",mu);
document.addEventListener("wheel",mwheel);
document.addEventListener("keydown",keyDown);
document.addEventListener("keyup",keyUp);


function keyStroke(key,keydown,keyup,code,ctrl,alt,shift,caps){
	this.key=key;
	this.keydown=keydown;
	this.keyup=keyup;
	this.code=code;
	this.ctrl="false";
	this.alt="false";
	this.shift="false";
	this.caps="nal";
}

var arr = new Array();

function keyDown(e){
	e = (e) ? e : window.event;
	var key = new keyStroke();
	key.keydown = Date.now();
	key.code=e.code;
	key.key=e.key;
	if(e.ctrlKey){
		key.ctrl="true";
	}
	if(e.altKey){
		// Original code set key.ctrl here by mistake, so the Alt column was
		// never recorded. Fixed to key.alt. (The thesis analysis only used the
		// Shift and CapsLock columns, so published results are unaffected.)
		key.alt="true";
	}
	if(e.shiftKey){
		key.shift="true";
	}
	if(e.key.length == 1 && /^[0-9]+$/.test(e.key)){
		key.caps="number";
	}
	if(e.key.length == 1 && /^[a-z]+$/.test(e.key)){
		key.caps="false";
	}
	if(e.key.length == 1 &&/^[A-Z]+$/.test(e.key)){
		key.caps="true";
	}
	arr.push(key);

//	console.log("new key created. Keycode: "+key.code+", key: "+key.key+", down: "+key.keydown);
}

function keyUp(e){
	e = (e) ? e : window.event;
	t = Date.now();
	for (var i=0;i<arr.length;i++){
		if(arr[arr.length-1-i].code == e.code){
			arr[arr.length-1-i].keyup=t;
			console.log(arr[arr.length-1-i]);
			var msg={
				type: "keystroke",
				data: arr[arr.length-1-i]
			}
			chrome.runtime.sendMessage(msg, function(response){
				console.log("yooo");
			})

			arr.splice(arr.length-1-i,1)
			console.log(arr)
		//	console.log(i+", keyup updated. Keycode: "+e.code+", keyup:"+arr[arr.length-1-i].keyup);
			break;
		}
	}
}

function mouseobj(t,x,y,ts){
	this.t=t;
	this.x=x;
	this.y=y;
	this.ts=ts;
}

function setobj(t,x,y,ts){
	var obj=new mouseobj()
	obj.t=t;
	obj.x=x;
	obj.y=y;
	obj.ts=ts;

	var msg={
		type:"mouse",
		data: obj
	}
	chrome.runtime.sendMessage(msg,function(response){
		console.log("mousesent")
	})


}


// Mouse timestamps are shifted back by a fixed number of days so the stored
// value is a smaller number and the absolute wall-clock time is obscured. The
// offset is constant, so all timing differences used by the analysis are
// preserved exactly.
var TIMESTAMP_OFFSET_MS = 17741*24*60*60*1000;

function mm(e){
	// Throttle move events to ~60 Hz (one every 16 ms) to keep data volume
	// manageable while still capturing the shape of the motion.
	if(this.time&&Date.now()-this.time<16) return
		this.time=Date.now()
    e = e||window.event
    var mp=mousePosition(e);
    var d = new Date()
    setobj(0,mp.x,mp.y,d.getTime()-TIMESTAMP_OFFSET_MS)
}

function md(e){
	var btn=e.button
    var mp=mousePosition(e);
    var d = new Date()    	
    timestamp=d.getTime()-TIMESTAMP_OFFSET_MS
    if(btn==0){
    	setobj(1,mp.x,mp.y,timestamp)
    }else if(btn==2){
    	setobj(3,mp.x,mp.y,timestamp)
    }else if(btn==1){	
    	setobj(5,mp.x,mp.y,timestamp)
    }else{
    	setobj(8,0,0,0)
    }
}

function mu(e){
	var btn=e.button
	var mp=mousePosition(e);
	var d = new Date()
	timestamp=d.getTime()-TIMESTAMP_OFFSET_MS
	if(btn==0){
		setobj(2,mp.x,mp.y,timestamp)
	}else if(btn==2){
		setobj(4,mp.x,mp.y,timestamp)
	}else if(btn==1){
		setobj(6,mp.x,mp.y,timestamp)
	}else{
		setobj(8,0,0,0)
	}
}

function mwheel(e){
	var mp=mousePosition(e);
	var d = new Date()
	timestamp=d.getTime()-TIMESTAMP_OFFSET_MS
	setobj(7,mp.x,mp.y,timestamp)
}

function mousePosition(ev){
	if(ev.pageX || ev.pageY){
		return {x:ev.pageX,y:ev.pageY};//firefor,chrome 
	}
	// Fallback for old browsers without pageX/pageY.
	return{
		x:ev.clientX + document.body.scrollLeft - document.body.clientLeft,
		y:ev.clientY + document.body.scrollTop - document.body.clientTop  // was misspelt "cleintY"
	};
}