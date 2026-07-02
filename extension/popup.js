
document.getElementById("login").addEventListener("click", login);
document.getElementById('logout').addEventListener("click", logout);
document.getElementById('checkstatus').addEventListener("click", checkstatus);

function sendtobg(str0,str1,str2){
  var msg={type: str0, data1: str1, data2:str2}
  chrome.runtime.sendMessage(msg,function(response){
    console.log(response.data)
    document.getElementById("logintest").innerText=response.data
  })
}
window.onload=function(){
  sendtobg("logintest","","");
}


function logout(){
  sendtobg("logout","","");
}

function checkstatus(){
  sendtobg("checkstatus","","");
}

function login() {
  var data1 = document.getElementById('uname').value;
  var data2 = document.getElementById('pwd').value;
  sendtobg("unamepwd",data1,data2)
}

