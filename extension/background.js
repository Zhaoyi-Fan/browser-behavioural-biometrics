// Background script: receives messages from the content script and popup, and
// relays them to the collection server. See contentscript.js for context.
var xmlhttp;

chrome.runtime.onMessage.addListener(
  function(request, sender, sendResponse) {
    console.log(sender.tab ?
                "from a content script:" + sender.tab.url :
                "from the extension?");
    if (request.type == "keystroke"){
 //     sendserver(JSON.stringify(request.data));
        sendhttp("sendks.asp?q=",JSON.stringify(request.data),function(){
        console.log(xmlhttp.responseText)
      })
        //console.log(JSON.stringify(request.data))
    }

    if(request.type=="mouse"){
        sendhttp("sendms.asp?q=",JSON.stringify(request.data),function(){
            console.log(xmlhttp.responseText)
        })
    }

    if(request.type=="unamepwd"){
    	console.log("usname recieved"+request.data1+request.data2)
    	if(request.data1=="" || request.data2==""){
    		console.log("empty input");
    		sendResponse({data:"empty input"})
            return;
    	}
        sendhttp("bglogin.asp?u=",request.data1+"&p="+request.data2,function(){
            if(xmlhttp.readyState==4 && xmlhttp.status==200){
                console.log(xmlhttp.responseText)
                sendResponse({data: xmlhttp.responseText})
            }
        });
    }

    if(request.type=="logout"){
        console.log("logout request recieved")
        sendhttp("logout.asp?q=","ojbk",function(){
            if(xmlhttp.readyState==4 && xmlhttp.status==200){
                console.log(xmlhttp.responseText)
                sendResponse({data: xmlhttp.responseText})
            }
        });
    }

    if(request.type=="checkstatus"){
        console.log("checkstatus recieved")
        sendhttp("showcookie.asp?q=","ojbk",function(){
            if(xmlhttp.readyState==4 && xmlhttp.status==200){
                console.log(xmlhttp.responseText)
                sendResponse({data: xmlhttp.responseText})
            }
        });
    }

    if(request.type=="register"){
        console.log("register recieved")
        sendhttp("exreg.asp?u=",request.u+"&p="+request.p+"&f="+request.f+"&l="+request.l,function(){
            if(xmlhttp.readyState==4 && xmlhttp.status==200){
                console.log(xmlhttp.responseText)
                sendResponse({data: xmlhttp.responseText})
            }
        });
    }

    if(request.type=="logintest"){
        console.log("logintest")
        sendhttp("logintest.asp?q=","hello",function(){
            if(xmlhttp.readyState==4 && xmlhttp.status==200){
                console.log(xmlhttp.responseText)
                sendResponse({data: xmlhttp.responseText})
            }
        });

    }

    return true;

  });
// The collection server that received the data during the experiments. The
// real host has been replaced with a placeholder for release - point this at
// your own server (with the matching .asp endpoints) if you want to run the
// tool. The server code is not part of this repository.
var SERVER_BASE_URL = "https://your-collection-server.example/";

// Fire a GET request to one of the server endpoints. Data is passed in the
// query string, which is how the original extension worked (a content script
// cannot post cross-origin directly, so the background script relays it).
function sendhttp(url,str,func){
    // xmlhttp is intentionally global: the onMessage callbacks above read
    // xmlhttp.responseText / readyState / status after the request completes.
    xmlhttp=new XMLHttpRequest();
    xmlhttp.onreadystatechange=func;
    xmlhttp.open("get",SERVER_BASE_URL+url+str,true)
    xmlhttp.send()
}
