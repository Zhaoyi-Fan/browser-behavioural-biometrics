document.getElementById("submit").addEventListener("click", submit);
document.getElementById("reset").addEventListener("click", reset);

function submit(){
  var username = document.getElementById('uname').value;
  var password = document.getElementById('pwd').value;
  var firstname = document.getElementById('firstname').value;
  var lastname = document.getElementById('lastname').value;

  var msg = {
    type: "register",
    u: username,
    p: password,
    f: firstname,
    l: lastname
  }

  chrome.runtime.sendMessage(msg,function(response){
    console.log(response.data)
    document.getElementById("regtest").innerHTML=response.data

    if(response.data=="Register successfully!"){
    	document.getElementById("regtest").innerHTML=document.getElementById("regtest").innerHTML+'Go to log in.'
    	document.getElementById("regtest").href="popup.html"
    }
  })
}

function reset(){
	document.getElementById('uname').value="";
	document.getElementById('pwd').value="";
	document.getElementById('firstname').value="";
	document.getElementById('lastname').value="";
}