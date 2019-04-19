
function lastPage(){
	history.go(-1);
}

function addJsonObj(jsonstr,name,value){
	if(jsonstr!="")
		jsonstr=jsonstr+",";
	jsonstr=jsonstr+'"'+name+'":'+'"'+value+'"';
	return jsonstr;
}

function getUrlParams() {
   var str=location.href; //取得整个地址栏
   var num=str.indexOf("?");
   strParams="";
   if(num >=0)
   	strParams=str.substr(num+1); //取得所有参
   return strParams;
}

function getUrlParam(name) {
    var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)", "i");
    var r = window.location.search.substr(1).match(reg);
    if (r != null) 
    	return decodeURI(decodeURI(unescape(r[2]))); 
    return "";
}

function addParamToUrl(url,pname,pvalue){
	var num=url.indexOf("?");
	if(num >=0)
		return url+"&"+encodeURI(pname)+"="+encodeURI(pvalue);
	else
		return url+"?"+encodeURI(pname)+"="+encodeURI(pvalue);
}

function getObjectURL(file) {
	var url = null ; 
	if (window.createObjectURL!=undefined) { // basic
		url = window.createObjectURL(file) ;
	} else if (window.URL!=undefined) { // mozilla(firefox)
		url = window.URL.createObjectURL(file) ;
	} else if (window.webkitURL!=undefined) { // webkit or chrome
		url = window.webkitURL.createObjectURL(file) ;
	}
	return url ;
}

//读取cookies 
function getCookie(name) 
{ 
 var arr,reg=new RegExp("(^| )"+name+"=([^;]*)(;|$)"); 
 if(arr=document.cookie.match(reg)) 
  return unescape(arr[2]); 
 else 
  return null; 
}

