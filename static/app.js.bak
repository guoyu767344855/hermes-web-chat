
var CURRENT_SESSION='session_current';
var currentImage=null,currentFile=null;
var chatMessages,messageInput,previewContainer,previewImage,filePreviewContainer,sendBtn;

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
function getFileIcon(name){var ext=name.split('.').pop().toLowerCase();var icons={pdf:'PDF',doc:'DOC',txt:'TXT',zip:'ZIP',jpg:'IMG',png:'IMG'};return icons[ext]||'FILE';}
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
                // 用户消息保留换行，助手消息用 marked 渲染
                var renderedContent=msg.isUser?msg.content.split('\n').join('<br>'):marked.parse(msg.content);
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

function saveChatHistory(){
    var sessionKey='hermes_chat_'+CURRENT_SESSION;
    try{
        var msgs=[];
        var divs=chatMessages.querySelectorAll('.message');
        for(var i=0;i<divs.length;i++){
            var div=divs[i];
            var isUser=div.classList.contains('user');
            var textDiv=div.querySelector('.message-text');
            var content=textDiv?textDiv.textContent:'';
            var img=div.querySelector('.message-image');
            msgs.push({content:content,isUser:isUser,imageData:img?img.src:null});
        }
        if(msgs.length>100)msgs=msgs.slice(-100);
        localStorage.setItem(sessionKey,JSON.stringify(msgs));
    }catch(e){console.error('Save error:',e);}
}

function addMessage(content,isUser,imageData,save){
    if(save===undefined)save=true;
    var div=document.createElement('div');
    div.className='message '+(isUser?'user':'assistant');
    // 使用 marked 渲染 Markdown（包括换行）
    var renderedContent=isUser?content:marked.parse(content);
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
    showLoading(); // 显示打字动画
    var buffer='';
    var assistantDiv=null;
    var textDiv=null;
    
    var xhr=new XMLHttpRequest();
    xhr.open('POST','/api/chat_stream',true);
    
    var position=0;
    xhr.onprogress=function(){
        // 移除加载动画，创建消息框（第一次收到数据时）
        if(!assistantDiv){
            removeLoading();
            assistantDiv=createAssistantMessage();
            textDiv=assistantDiv.querySelector('.message-text');
        }
        
        var text=xhr.responseText.substring(position);
        position=xhr.responseText.length;
        buffer+=text;
        
        // 按 SSE 协议格式解析：每行以 data: 开头
        var NL=String.fromCharCode(10);
        var lines=buffer.split(NL);
        buffer=lines.pop()||'';
        
        for(var i=0;i<lines.length;i++){
            var line=lines[i].trim();
            if(line.startsWith('data: ')){
                var data=line.substring(6);
                if(data==='[DONE]'){
                    sendBtn.disabled=false;
                    messageInput.focus();
                    saveChatHistory();
                    return;
                }
                // 保留换行符，让 marked 正确解析 Markdown
                if(textDiv.textContent.length>0 && !textDiv.textContent.endsWith(NL)){
                    textDiv.textContent+=NL;
                }
                textDiv.textContent+=data;
                // 实时渲染 Markdown
                textDiv.innerHTML=marked.parse(textDiv.textContent);
                chatMessages.scrollTop=chatMessages.scrollHeight;
            }
        }
    };
    
    xhr.onload=function(){
        if(xhr.status!==200){
            if(textDiv) textDiv.textContent+=NL+'[发送失败]';
        }
        sendBtn.disabled=false;
        messageInput.focus();
        saveChatHistory();
    };
    
    xhr.onerror=function(){
        if(textDiv) textDiv.textContent+=NL+'[网络错误]';
        sendBtn.disabled=false;
        messageInput.focus();
    };
    
    xhr.send(formData);
}

// 打字机效果显示文本
function typeText(text, textDiv){
    var chars=text.split('');
    var index=0;
    function type(){
        if(index<chars.length){
            textDiv.textContent+=chars[index];
            index++;
            chatMessages.scrollTop=chatMessages.scrollHeight;
            setTimeout(type, 10+Math.random()*20); // 随机打字速度
        }
    }
    type();
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
    div.innerHTML='<div class="message-avatar">🤖</div><div class="message-content"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>';
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
        var match=item.match(/^> (\d{4}-\d{2}-\d{2})/);
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
        for(var i=0;i<data.sessions.length;i++){
            var s=data.sessions[i];
            var SQ=String.fromCharCode(39);
            var DQ=String.fromCharCode(34);
            var safeTitle=String(s.title||'未命名').replace(new RegExp(SQ,'g'),'\x27').replace(new RegExp(DQ,'g'),'\x22');
            html+='<li class="session-item" data-session-id="'+s.id+'" data-session-title="'+safeTitle+'" style="cursor:pointer;">';
            html+='<strong>'+(s.title||'未命名')+'</strong><br>';
            html+='<small>'+(s.created||'')+' | '+s.messages+'条</small>';
            html+='</li>';
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
                // 保存到 localStorage
                localStorage.setItem(sessionKey,JSON.stringify(data.messages));
            }else{
                chatMessages.innerHTML='';
                addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
            }
        })
        .catch(function(e){
            console.error('Load session detail error:',e);
            chatMessages.innerHTML='';
            addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
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
        var renderedContent=msg.isUser?msg.content.split(NL).join('<br>'):marked.parse(msg.content);
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
    var html='<div class="card"><pre style="background:#0f0f1a;padding:15px;border-radius:8px;white-space:pre-wrap;">'+(data.raw||'暂无数据')+'</pre></div>';
    var page=renderRaw.currentPage||'cron';
    document.getElementById(page+'-content').innerHTML=html;
}

function renderStats(data){
    var html='<div class="stats-grid">';
    if(data.sessions!==undefined)html+='<div class="stat-card"><div class="stat-value">'+data.sessions+'</div><div class="stat-label">会话数</div></div>';
    if(data.total_tokens!==undefined)html+='<div class="stat-card"><div class="stat-value">'+data.total_tokens+'</div><div class="stat-label">Token</div></div>';
    if(data.estimated_cost)html+='<div class="stat-card"><div class="stat-value">'+data.estimated_cost+'</div><div class="stat-label">费用</div></div>';
    if(data.peak_hour)html+='<div class="stat-card"><div class="stat-value">'+data.peak_hour+':00</div><div class="stat-label">高峰时段</div></div>';
    html+='</div>';
    var page=renderStats.currentPage||'costs';
    document.getElementById(page+'-content').innerHTML=html;
}
    