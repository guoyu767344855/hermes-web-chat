// Hermes Web Chat - Enhanced JavaScript
// Optimized for better Markdown rendering and session management

var CURRENT_SESSION='session_current';
var currentImage=null,currentFile=null;
var chatMessages,messageInput,previewContainer,previewImage,filePreviewContainer,sendBtn;

// Configure marked.js for better Markdown rendering
if(typeof marked!=='undefined'){
    marked.setOptions({
        breaks:true,           // Convert \n to <br>
        gfm:true,              // GitHub Flavored Markdown
        headerIds:true,        // Add IDs to headers
        mangle:false,          // Don't escape header IDs
        sanitize:false         // Don't sanitize HTML (allow custom styling)
    });
}

window.onload=function(){
    chatMessages=document.getElementById('chatMessages');
    messageInput=document.getElementById('messageInput');
    previewContainer=document.getElementById('previewContainer');
    previewImage=document.getElementById('previewImage');
    filePreviewContainer=document.getElementById('filePreviewContainer');
    sendBtn=document.getElementById('sendBtn');
    initMenu();
    loadChatHistory();
    setupInput();
    loadTheme();
};

function initMenu(){
    var items=document.querySelectorAll('.menu-item');
    for(var i=0;i<items.length;i++){
        items[i].onclick=function(){
            var page=this.getAttribute('data-page');
            var allItems=document.querySelectorAll('.menu-item');
            for(var j=0;j<allItems.length;j++)allItems[j].classList.remove('active');
            this.classList.add('active');
            var allPages=document.querySelectorAll('.page');
            for(var j=0;j<allPages.length;j++)allPages[j].classList.remove('active');
            document.getElementById('page-'+page).classList.add('active');
            if(page==='memory')loadMemory();
            else if(page==='skills')loadSkills();
            else if(page==='sessions')loadSessions();
            else if(page==='cron')loadCron();
            else if(page==='projects')loadProjects();
            else if(page==='costs')loadCosts();
            else if(page==='patterns')loadPatterns();
            else if(page==='settings')loadSettings();
        };
    }
}

function createNewSession(){
    var now=new Date();
    var sessionName='session_'+now.toISOString().replace(/[:-]/g,'').split('.')[0].replace('T','_');
    CURRENT_SESSION=sessionName;
    chatMessages.innerHTML='';
    addMessage('✨ 新会话已创建！有什么可以帮你的吗？',false,null,false);
    updateSessionTitle();
}

function updateSessionTitle(){
    var title=CURRENT_SESSION.replace(/_/g,' ').replace('session ','');
    document.getElementById('currentSessionTitle').textContent='💬 '+title;
}

function switchSession(sessionId){
    CURRENT_SESSION=sessionId;
    loadChatHistory();
    updateSessionTitle();
    var allItems=document.querySelectorAll('.menu-item');
    for(var j=0;j<allItems.length;j++)allItems[j].classList.remove('active');
    allItems[0].classList.add('active');
    var allPages=document.querySelectorAll('.page');
    for(var j=0;j<allPages.length;j++)allPages[j].classList.remove('active');
    document.getElementById('page-chat').classList.add('active');
}

function setupInput(){
    messageInput.addEventListener('input',function(){this.style.height='auto';this.style.height=Math.min(this.scrollHeight,150)+'px';});
    messageInput.addEventListener('paste',function(e){
        var items=e.clipboardData.items;
        for(var i=0;i<items.length;i++){
            if(items[i].type.indexOf('image')!==-1){
                e.preventDefault();
                var blob=items[i].getAsFile();
                var reader=new FileReader();
                reader.onload=function(evt){currentImage=evt.target.result;showPreview(currentImage);};
                reader.readAsDataURL(blob);
                break;
            }
        }
    });
    messageInput.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}});
    document.getElementById('imageInput').addEventListener('change',handleImageSelect);
    document.getElementById('fileInput').addEventListener('change',handleFileSelect);
}

function showPreview(data){previewImage.src=data;previewContainer.classList.add('show');}
function removeImage(){currentImage=null;previewContainer.classList.remove('show');document.getElementById('imageInput').value='';}
function removeFile(){currentFile=null;filePreviewContainer.classList.remove('show');document.getElementById('fileInput').value='';}
function getFileIcon(name){var ext=name.split('.').pop().toLowerCase();var icons={pdf:'📄',doc:'📝',docx:'📝',txt:'📄',md:'📄',py:'🐍',js:'📜',json:'📋',zip:'📦',rar:'📦',jpg:'🖼️',jpeg:'🖼️',png:'🖼️',gif:'🖼️'};return icons[ext]||'📎';}
function formatFileSize(bytes){if(bytes<1024)return bytes+' B';if(bytes<1048576)return (bytes/1024).toFixed(1)+' KB';return (bytes/1048576).toFixed(1)+' MB';}
function handleImageSelect(e){var file=e.target.files[0];if(file){var reader=new FileReader();reader.onload=function(evt){currentImage=evt.target.result;showPreview(currentImage);};reader.readAsDataURL(file);}}
function handleFileSelect(e){var file=e.target.files[0];if(file){currentFile=file;document.getElementById('filePreviewIcon').innerHTML=getFileIcon(file.name);document.getElementById('filePreviewName').textContent=file.name;document.getElementById('filePreviewSize').textContent=formatFileSize(file.size);filePreviewContainer.classList.add('show');}}

function loadChatHistory(){
    var sessionKey='hermes_chat_'+CURRENT_SESSION;
    try{
        var saved=localStorage.getItem(sessionKey);
        if(saved){
            var history=JSON.parse(saved);
            chatMessages.innerHTML='';
            for(var i=0;i<history.length;i++){
                var msg=history[i];
                var div=document.createElement('div');
                div.className='message '+(msg.isUser?'user':'assistant');
                // 用户消息保留换行，助手消息直接使用保存的 HTML（已渲染的 Markdown）
                var renderedContent=msg.isUser?escapeHtml(msg.content).split('\n').join('<br>'):msg.content;
                var html='<div class="message-avatar">'+(msg.isUser?'👤':'🤖')+'</div><div class="message-content"><div class="message-text">'+renderedContent+'</div>';
                if(msg.imageData)html+='<img class="message-image" src="'+msg.imageData+'">';
                html+='</div>';
                div.innerHTML=html;
                if(msg.isUser){div.style.cursor='pointer';div.title='右键点击重新编辑';div.oncontextmenu=function(e){e.preventDefault();editMessage(this);};}
                chatMessages.appendChild(div);
            }
            chatMessages.scrollTop=chatMessages.scrollHeight;
        }else{
            chatMessages.innerHTML='';
            addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
        }
    }catch(e){console.error('Load error:',e);}
}

// 检查 localStorage 剩余空间（字节）
function getLocalStorageQuota(){
    try{
        var testKey='__quota_test__';
        var start=Date.now();
        var str='x';
        while(str.length<1048576){str+=str;} // 快速生成 1MB 字符串
        var i=0;
        while(i<5242880){ // 最多尝试 5MB
            localStorage.setItem(testKey,str.substring(0,i));
            i+=10240; // 每次增加 10KB
        }
        localStorage.removeItem(testKey);
        return i;
    }catch(e){
        localStorage.removeItem('__quota_test__');
        return 0;
    }
}

// 估算字符串大小（字节）
function estimateSize(str){return new Blob([str]).size;}

// 检查是否会超出配额
function willExceedQuota(key,newValue){
    try{
        var currentSize=0;
        for(var k in localStorage){
            if(localStorage.hasOwnProperty(k)){
                currentSize+=estimateSize(localStorage[k]);
            }
        }
        var newSize=estimateSize(newValue);
        // localStorage 通常限制 5-10MB，保守估计 4MB
        return (currentSize+newSize)>4194304;
    }catch(e){
        return true; // 出错时假设会超限
    }
}

function saveChatHistory(){
    var sessionKey='hermes_chat_'+CURRENT_SESSION;
    try{
        var msgs=[];
        var divs=chatMessages.querySelectorAll('.message');
        for(var i=0;i<divs.length;i++){
            var div=divs[i];
            var isUser=div.classList.contains('user');
            var textDiv=div.querySelector('.message-text');
            // 助手消息保存 innerHTML（已渲染的 Markdown），用户消息保存 textContent
            var content=isUser?(textDiv?textDiv.textContent:''):(textDiv?textDiv.innerHTML:'');
            var img=div.querySelector('.message-image');
            // 优化：如果图片是 base64 且较大，不存储到 localStorage
            var imgData=null;
            if(img){
                var src=img.src;
                // 如果是 base64 且超过 100KB，不存储
                if(src.startsWith('data:')&&src.length>102400){
                    imgData=null; // 不存储大图片
                    console.log('Skip storing large image to localStorage');
                }else{
                    imgData=src;
                }
            }
            msgs.push({content:content,isUser:isUser,imageData:imgData});
        }
        if(msgs.length>100)msgs=msgs.slice(-100);
        var jsonData=JSON.stringify(msgs);
        // 检查是否会超出配额
        if(willExceedQuota(sessionKey,jsonData)){
            console.warn('LocalStorage quota warning, storing without images');
            // 移除所有图片数据后重试
            for(var j=0;j<msgs.length;j++){
                msgs[j].imageData=null;
            }
            jsonData=JSON.stringify(msgs);
        }
        localStorage.setItem(sessionKey,jsonData);
    }catch(e){
        console.error('Save error:',e);
        // 如果保存失败，尝试清理旧会话
        if(e.name==='QuotaExceededError'){
            clearOldSessions();
        }
    }
}

// 清理 7 天前的旧会话
function clearOldSessions(){
    try{
        var now=new Date();
        var cutoff=new Date(now.getTime()-7*24*60*60*1000); // 7 天前
        var keysToRemove=[];
        for(var k in localStorage){
            if(k.startsWith('hermes_chat_session_')){
                var dateStr=k.replace('hermes_chat_session_','').substring(0,8);
                if(dateStr.length===8){
                    var year=parseInt(dateStr.substring(0,4));
                    var month=parseInt(dateStr.substring(4,6))-1;
                    var day=parseInt(dateStr.substring(6,8));
                    var sessionDate=new Date(year,month,day);
                    if(sessionDate<cutoff){
                        keysToRemove.push(k);
                    }
                }
            }
        }
        for(var i=0;i<keysToRemove.length;i++){
            localStorage.removeItem(keysToRemove[i]);
            console.log('Removed old session:',keysToRemove[i]);
        }
    }catch(e){
        console.error('Clear old sessions error:',e);
    }
}

// HTML 转义函数，防止 XSS
function escapeHtml(text){
    var map={'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'};
    return text.replace(/[&<>"']/g,function(m){return map[m];});
}

function addMessage(content,isUser,imageData,save){
    if(save===undefined)save=true;
    var div=document.createElement('div');
    div.className='message '+(isUser?'user':'assistant');
    // 用户消息进行 HTML 转义后保留换行，助手消息用 marked 渲染 Markdown
    var renderedContent=isUser?escapeHtml(content).split('\n').join('<br>'):marked.parse(content);
    var html='<div class="message-avatar">'+(isUser?'👤':'🤖')+'</div><div class="message-content"><div class="message-text">'+renderedContent+'</div>';
    if(imageData)html+='<img class="message-image" src="'+imageData+'">';
    html+='</div>';
    div.innerHTML=html;
    if(isUser){div.style.cursor='pointer';div.title='右键点击重新编辑';div.oncontextmenu=function(e){e.preventDefault();editMessage(this);};}
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    if(save)saveChatHistory();
}

function editMessage(msgDiv){
    var textDiv=msgDiv.querySelector('.message-text');
    var content=textDiv?textDiv.textContent:'';
    if(confirm('确定要重新编辑这条消息吗？')){
        messageInput.value=content;
        messageInput.style.height='auto';
        messageInput.style.height=Math.min(messageInput.scrollHeight,150)+'px';
        messageInput.focus();
        msgDiv.remove();
        saveChatHistory();
    }
}

function typeMessage(content){
    var div=document.createElement('div');
    div.className='message assistant';
    var html='<div class="message-avatar">🤖</div><div class="message-content"><div class="message-text"></div></div>';
    div.innerHTML=html;
    chatMessages.appendChild(div);
    var textDiv=div.querySelector('.message-text');
    // 使用 marked 渲染 Markdown 内容（保留换行和格式）
    textDiv.innerHTML=marked.parse(content);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    saveChatHistory();
}

function sendMessage(){
    var message=messageInput.value.trim();
    if(!message&&!currentImage&&!currentFile)return;
    sendBtn.disabled=true;
    var userMsg=message;
    var imgData=currentImage;
    if(currentImage)userMsg+=(userMsg?' [图片]':'[图片]');
    if(currentFile)userMsg+=(userMsg?' [文件:'+currentFile.name+']':'[文件:'+currentFile.name+']');
    addMessage(userMsg,true,imgData);
    messageInput.value='';
    messageInput.style.height='auto';
    var fileToSend=currentFile;
    var imageToSend=currentImage;
    removeImage();
    removeFile();
    var formData=new FormData();
    formData.append('message',message||'请分析');
    if(imageToSend){
        dataURLtoBlob(imageToSend).then(function(blob){
            formData.append('image',blob,'image.png');
            sendStreamRequest(formData,fileToSend);
        }).catch(function(err){
            console.error('Convert image error:',err);
            sendStreamRequest(formData,fileToSend);
        });
    }else{sendStreamRequest(formData,fileToSend);}
}

// 将 dataURL 或 URL 转换为 blob
function dataURLtoBlob(dataURL){
    return new Promise(function(resolve,reject){
        if(dataURL.startsWith('data:')){
            // base64 data URL
            var parts=dataURL.split(',');
            var mime=parts[0].match(/:(.*?);/)[1];
            var bstr=atob(parts[1]);
            var n=bstr.length;
            var u8arr=new Uint8Array(n);
            while(n--){u8arr[n]=bstr.charCodeAt(n);}
            resolve(new Blob([u8arr],{type:mime}));
        }else{
            // HTTP URL
            fetch(dataURL).then(function(r){return r.blob();}).then(resolve).catch(reject);
        }
    });
}

function sendRequest(formData,file){
    if(file)formData.append('file',file);
    fetch('/api/chat',{method:'POST',body:formData}).then(function(r){return r.json();}).then(function(data){
        removeLoading();
        typeMessage(data.response);
        sendBtn.disabled=false;
        messageInput.focus();
    }).catch(function(err){
        removeLoading();
        addMessage('发送失败：'+err.message,false,null);
        sendBtn.disabled=false;
    });
}

function sendStreamRequest(formData,file){
    if(file)formData.append('file',file);
    showLoading();
    var buffer='';
    var assistantDiv=null;
    var textDiv=null;
    var thinkingContentDiv=null;
    var thinkingContent='';
    var firstContent=true;
    var startTime=Date.now();
    var progressTimer=null;
    
    var xhr=new XMLHttpRequest();
    xhr.open('POST','/api/chat_stream',true);
    
    var position=0;
    xhr.onprogress=function(){
        var text=xhr.responseText.substring(position);
        position=xhr.responseText.length;
        buffer+=text;
        
        // 按行解析 SSE 协议
        var NL=String.fromCharCode(10);
        var lines=buffer.split(NL);
        buffer=lines.pop()||'';
        
        for(var i=0;i<lines.length;i++){
            var line=lines[i];
            if(line.startsWith('data: ')){
                var data=line.substring(6);
                if(data==='[DONE]'){
                    if(progressTimer) clearInterval(progressTimer);
                    if(thinkingContentDiv){
                        var thinkingContainer=thinkingContentDiv.closest('.thinking-container');
                        if(thinkingContainer){
                            removeLoading();
                            assistantDiv=createAssistantMessage();
                            textDiv=assistantDiv.querySelector('.message-text');
                            textDiv.innerHTML=marked.parse(thinkingContent);
                            chatMessages.scrollTop=chatMessages.scrollHeight;
                            thinkingContainer.remove();
                        }
                    }
                    sendBtn.disabled=false;
                    messageInput.focus();
                    saveChatHistory();
                    return;
                }
                if(data==='') continue;
                if(firstContent){
                    thinkingContentDiv=document.getElementById('thinkingContent');
                    firstContent=false;
                    if(progressTimer) clearInterval(progressTimer);
                }
                if(data.trim()){
                    thinkingContent+=data+'\n';
                    if(thinkingContentDiv){
                        thinkingContentDiv.innerHTML=marked.parse(thinkingContent);
                        thinkingContentDiv.scrollTop=thinkingContentDiv.scrollHeight;
                    }
                }
            }
        }
    };
    
    // 启动进度提示定时器
    progressTimer=setInterval(function(){
        var elapsed=((Date.now()-startTime)/1000).toFixed(1);
        var progressDiv=document.getElementById('thinkingContent');
        if(progressDiv && firstContent){
            progressDiv.innerHTML='<p style="color:#888">正在思考中... 已 '+elapsed+' 秒</p>';
        }
    }, 1000);
    
    xhr.onload=function(){
        if(xhr.status!==200){
            if(textDiv) textDiv.innerHTML=marked.parse(textDiv.textContent+'\\n\\n**[发送失败]**');
        }
        sendBtn.disabled=false;
        messageInput.focus();
        saveChatHistory();
    };
    
    xhr.onerror=function(){
        if(textDiv) textDiv.innerHTML=marked.parse(textDiv.textContent+'\\n\\n**[网络错误]**');
        sendBtn.disabled=false;
        messageInput.focus();
    };
    
    xhr.send(formData);
}

function createAssistantMessage(){
    var div=document.createElement('div');
    div.className='message assistant';
    var html='<div class="message-avatar">🤖</div><div class="message-content"><div class="message-text"></div></div>';
    div.innerHTML=html;
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    return div;
}

function showLoading(){
    var div=document.createElement('div');
    div.className='message assistant';
    div.id='loadingMsg';
    div.innerHTML='<div class="message-avatar">🤖</div><div class="message-content"><div class="thinking-container"><div class="thinking-header"><svg class="thinking-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path></svg>思考中...</div><div class="thinking-content" id="thinkingContent"></div></div></div>';
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
}

function removeLoading(){var div=document.getElementById('loadingMsg');if(div)div.remove();}
function clearChatHistory(){if(confirm('确定清空当前对话？')){var sessionKey='hermes_chat_'+CURRENT_SESSION;localStorage.removeItem(sessionKey);chatMessages.innerHTML='';addMessage('对话已清空',false,null,false);}}

// 存储原始数据用于筛选
var allSessionsData=[];
var allMemoryData=[];

function loadMemory(){
    renderList.currentPage='memory';
    fetch('/api/memory').then(function(r){return r.json();}).then(function(data){
        allMemoryData=data;
        renderList(data);
    });
}
function loadSessions(){
    renderList.currentPage='sessions';
    fetch('/api/sessions').then(function(r){return r.json();}).then(function(data){
        allSessionsData=data;
        renderList(data);
    });
}
function filterSessions(){
    var days=document.getElementById('sessionDateFilter').value;
    if(days==='all'){renderList(allSessionsData);return;}
    var cutoff=new Date();
    cutoff.setDate(cutoff.getDate()-parseInt(days));
    var filtered={sessions:allSessionsData.sessions.filter(function(s){
        var d=new Date(s.created||'');
        return d>=cutoff;
    })};
    renderList(filtered);
}
function filterMemory(){
    var days=document.getElementById('memoryDateFilter').value;
    if(days==='all'){renderList(allMemoryData);return;}
    var cutoff=new Date();
    cutoff.setDate(cutoff.getDate()-parseInt(days));
    var filtered={daily:allMemoryData.daily.filter(function(item){
        var match=item.match(/^> (\\d{4}-\\d{2}-\\d{2})/);
        if(!match)return false;
        var d=new Date(match[1]);
        return d>=cutoff;
    }),long_term:allMemoryData.long_term,file_path:allMemoryData.file_path};
    renderList(filtered);
}
function loadSkills(){renderList.currentPage='skills';fetch('/api/skills').then(function(r){return r.json();}).then(renderList);}
function loadCron(){renderRaw.currentPage='cron';fetch('/api/cron').then(function(r){return r.json();}).then(renderRaw);}
function loadProjects(){renderList.currentPage='projects';fetch('/api/projects').then(function(r){return r.json();}).then(renderList);}
function loadCosts(){renderStats.currentPage='costs';fetch('/api/costs').then(function(r){return r.json();}).then(renderStats);}
function loadPatterns(){renderStats.currentPage='patterns';fetch('/api/patterns').then(function(r){return r.json();}).then(renderStats);}

function renderList(data){
    var html='<div class="card"><ul class="data-list">';
    if(data.skills){
        // 按分类分组
        var byCategory={};
        for(var i=0;i<data.skills.length;i++){
            var s=data.skills[i];
            var cat=s.category||'其他';
            if(!byCategory[cat])byCategory[cat]=[];
            byCategory[cat].push(s);
        }
        // 排序分类
        var categories=Object.keys(byCategory).sort();
        for(var j=0;j<categories.length;j++){
            var cat=categories[j];
            html+='<li style="background:rgba(0,217,255,0.15);border-left-color:#00ff88;"><strong style="color:#00ff88;">📁 '+cat+' ('+byCategory[cat].length+')</strong></li>';
            for(var i=0;i<byCategory[cat].length;i++){
                var s=byCategory[cat][i];
                var badge=s.source==='local'?'<span style="background:#00d9ff;color:#0f0f1a;padding:2px 6px;border-radius:4px;font-size:11px;margin-left:8px;">本地</span>':'';
                html+='<li style="padding:8px 15px;"><code style="background:#0f0f1a;padding:4px 8px;border-radius:4px;color:#00d9ff;">'+s.name+'</code>'+badge+'</li>';
            }
        }
    }
    else if(data.sessions){
        if(data.sessions.length===0){
            html+='<li style="color:#666;text-align:center;padding:20px;">暂无会话数据</li>';
        }else{
            for(var i=0;i<data.sessions.length;i++){
                var s=data.sessions[i];
                var SQ=String.fromCharCode(39);
                var DQ=String.fromCharCode(34);
                var safeTitle=String(s.title||'未命名').replace(new RegExp(SQ,'g'),'\\x27').replace(new RegExp(DQ,'g'),'\\x22');
                html+='<li class="session-item" data-session-id="'+s.id+'" data-session-title="'+safeTitle+'" style="cursor:pointer;">';
                html+='<strong>'+(s.title||'未命名')+'</strong><br>';
                html+='<small>'+(s.created||'')+' | '+s.messages+' 条</small>';
                html+='</li>';
            }
        }
    }
    else if(data.projects||data.daily){
        var items=data.projects||data.daily;
        if(items && items.length>0){
            for(var i=0;i<items.length;i++)html+='<li>'+items[i]+'</li>';
        }else{
            html+='<li style="color:#666;text-align:center;padding:20px;">暂无数据</li>';
        }
    }
    else if(data.skills!==undefined && data.skills.length===0){
        html+='<li style="color:#666;text-align:center;padding:20px;">暂无技能数据</li>';
    }
    else if(data.sessions!==undefined && data.sessions.length===0){
        html+='<li style="color:#666;text-align:center;padding:20px;">暂无会话数据</li>';
    }
    else{html+='<li>暂无数据</li>';}
    html+='</ul></div>';
    var page=renderList.currentPage||'memory';
    var contentDiv=document.getElementById(page+'-content');
    contentDiv.innerHTML=html;
    // 绑定会话点击事件
    if(data.sessions){
        var items=contentDiv.querySelectorAll('.session-item');
        for(var i=0;i<items.length;i++){
            items[i].onclick=function(){
                var sessionId=this.getAttribute('data-session-id');
                var sessionTitle=this.getAttribute('data-session-title');
                openSession(sessionId,sessionTitle);
            };
        }
    }
}

function openSession(sessionId,sessionTitle){
    CURRENT_SESSION=sessionId;
    updateSessionTitle();
    loadSessionDetail();
    // 切换到聊天页面
    var allItems=document.querySelectorAll('.menu-item');
    for(var j=0;j<allItems.length;j++)allItems[j].classList.remove('active');
    allItems[0].classList.add('active');
    var allPages=document.querySelectorAll('.page');
    for(var j=0;j<allPages.length;j++)allPages[j].classList.remove('active');
    document.getElementById('page-chat').classList.add('active');
}

function loadSessionDetail(){
    var sessionKey='hermes_chat_'+CURRENT_SESSION;
    // 先尝试从 localStorage 加载
    var saved=localStorage.getItem(sessionKey);
    if(saved){
        var history=JSON.parse(saved);
        renderChatHistory(history);
        return;
    }
    // 从服务器加载历史会话
    fetch('/api/session_detail?session_id='+encodeURIComponent(CURRENT_SESSION))
        .then(function(r){return r.json();})
        .then(function(data){
            if(data.messages && data.messages.length>0){
                renderChatHistory(data.messages);
                // 优化：只存储不带大图片的数据到 localStorage
                var msgsToStore=[];
                for(var i=0;i<data.messages.length;i++){
                    var msg=data.messages[i];
                    // 如果图片是 base64 且超过 100KB，不存储
                    if(msg.imageData && msg.imageData.startsWith('data:') && msg.imageData.length>102400){
                        msgsToStore.push({content:msg.content,isUser:msg.isUser,imageData:null});
                        console.log('Skip storing large image from server response');
                    }else{
                        msgsToStore.push(msg);
                    }
                }
                // 检查配额后再存储
                try{
                    var jsonData=JSON.stringify(msgsToStore);
                    if(willExceedQuota(sessionKey,jsonData)){
                        console.warn('LocalStorage quota warning for server-loaded session');
                        // 移除所有图片
                        for(var j=0;j<msgsToStore.length;j++){
                            msgsToStore[j].imageData=null;
                        }
                        jsonData=JSON.stringify(msgsToStore);
                    }
                    localStorage.setItem(sessionKey,jsonData);
                }catch(e){
                    console.error('Save server session error:',e);
                }
            }else{
                chatMessages.innerHTML='';
                addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
            }
        })
        .catch(function(e){
            console.error('Load session detail error:',e);
            chatMessages.innerHTML='';
            addMessage('⚠️ 加载会话失败：'+e.message,false,null,false);
        });
}

function renderChatHistory(history){
    chatMessages.innerHTML='';
    var NL=String.fromCharCode(10);
    for(var i=0;i<history.length;i++){
        var msg=history[i];
        var div=document.createElement('div');
        div.className='message '+(msg.isUser?'user':'assistant');
        // 用户消息保留换行，助手消息用 marked 渲染
        var renderedContent=msg.isUser?escapeHtml(msg.content).split(NL).join('<br>'):marked.parse(msg.content);
        var html='<div class="message-avatar">'+(msg.isUser?'👤':'🤖')+'</div><div class="message-content"><div class="message-text">'+renderedContent+'</div>';
        if(msg.imageData)html+='<img class="message-image" src="'+msg.imageData+'">';
        html+='</div>';
        div.innerHTML=html;
        if(msg.isUser){div.style.cursor='pointer';div.title='右键点击重新编辑';div.oncontextmenu=function(e){e.preventDefault();editMessage(this);};}
        chatMessages.appendChild(div);
    }
    chatMessages.scrollTop=chatMessages.scrollHeight;
}

function renderRaw(data){
    var html='<div class="card"><pre style="background:#0f0f1a;padding:15px;border-radius:8px;white-space:pre-wrap;overflow-x:auto;">'+escapeHtml(data.raw||'暂无数据')+'</pre></div>';
    var page=renderRaw.currentPage||'cron';
    document.getElementById(page+'-content').innerHTML=html;
}

function renderStats(data){
    var html='<div class="stats-grid">';
    if(data.sessions!==undefined)html+='<div class="stat-card"><div class="stat-value">'+data.sessions+'</div><div class="stat-label">会话数</div></div>';
    if(data.total_tokens!==undefined)html+='<div class="stat-card"><div class="stat-value">'+(data.total_tokens/1000).toFixed(1)+'k</div><div class="stat-label">Token 用量</div></div>';
    if(data.estimated_cost)html+='<div class="stat-card"><div class="stat-value">'+data.estimated_cost+'</div><div class="stat-label">预估费用</div></div>';
    if(data.peak_hour)html+='<div class="stat-card"><div class="stat-value">'+data.peak_hour+':00</div><div class="stat-label">高峰时段</div></div>';
    html+='</div>';
    
    // 添加模型分布
    if(data.models){
        html+='<div class="card" style="margin-top:20px;"><h3 style="color:#00d9ff;margin-bottom:15px;">📊 模型使用分布</h3><ul class="data-list">';
        for(var model in data.models){
            html+='<li><code style="background:#0f0f1a;padding:4px 8px;border-radius:4px;color:#00d9ff;">'+model+'</code> <span style="color:#888;margin-left:10px;">'+data.models[model]+' 次会话</span></li>';
        }
        html+='</ul></div>';
    }
    
    var page=renderStats.currentPage||'costs';
    document.getElementById(page+'-content').innerHTML=html;
}

// 主题切换功能
function loadTheme(){
    var savedTheme=localStorage.getItem('hermes_theme')||'light';
    applyTheme(savedTheme);
}

function switchTheme(theme){
    applyTheme(theme);
    localStorage.setItem('hermes_theme',theme);
    updateThemeCards(theme);
}

function applyTheme(theme){
    if(theme==='light'||theme===''){
        document.documentElement.removeAttribute('data-theme');
    }else{
        document.documentElement.setAttribute('data-theme',theme);
    }
    updateThemeCards(theme);
}

function updateThemeCards(activeTheme){
    var cards=document.querySelectorAll('.theme-card');
    for(var i=0;i<cards.length;i++){
        if(cards[i].getAttribute('data-theme')===activeTheme){
            cards[i].classList.add('active');
        }else{
            cards[i].classList.remove('active');
        }
    }
}

function loadSettings(){
    // 设置页面不需要加载数据，主题状态已保存
    var savedTheme=localStorage.getItem('hermes_theme')||'light';
    updateThemeCards(savedTheme);
    // 显示存储信息
    displayStorageInfo();
}

// 显示存储使用信息
function displayStorageInfo(){
    try{
        var totalSize=0;
        var sessionCount=0;
        for(var k in localStorage){
            if(localStorage.hasOwnProperty(k)){
                totalSize+=estimateSize(localStorage[k]);
                if(k.startsWith('hermes_chat_'))sessionCount++;
            }
        }
        var sizeStr=totalSize<1024?totalSize+' B':(totalSize<1048576?(totalSize/1024).toFixed(1)+' KB':(totalSize/1048576).toFixed(2)+' MB');
        var infoDiv=document.getElementById('storageInfo');
        if(infoDiv){
            infoDiv.innerHTML='📊 当前使用：<strong>'+sizeStr+'</strong> | 会话数：<strong>'+sessionCount+'</strong>';
        }
    }catch(e){
        console.error('Display storage info error:',e);
    }
}

// 清理所有本地会话数据
function clearAllLocalStorage(){
    if(!confirm('确定要清理所有本地会话数据吗？\\n\\n注意：\\n1. 这将删除所有保存在浏览器的聊天记录\\n2. 服务器上的会话历史不会受影响\\n3. 当前会话也会被清空\\n\\n此操作不可恢复！')){
        return;
    }
    try{
        var keysToRemove=[];
        for(var k in localStorage){
            if(k.startsWith('hermes_chat_')){
                keysToRemove.push(k);
            }
        }
        for(var i=0;i<keysToRemove.length;i++){
            localStorage.removeItem(keysToRemove[i]);
        }
        // 清空当前聊天界面
        chatMessages.innerHTML='';
        addMessage('🗑️ 本地会话数据已清理',false,null,false);
        displayStorageInfo();
        alert('已清理 '+keysToRemove.length+' 个会话数据');
    }catch(e){
        alert('清理失败：'+e.message);
    }
}
