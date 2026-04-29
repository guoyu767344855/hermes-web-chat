// Hermes Web Chat - Enhanced JavaScript
// Optimized for better Markdown rendering and session management

var CURRENT_SESSION='session_current';
var currentImage=null,currentFile=null;
var chatMessages,messageInput,previewContainer,previewImage,filePreviewContainer,sendBtn;
var currentXhr=null;  // 保存当前请求，用于中止
var isThinking=false;  // 标记是否正在思考中

// IndexedDB 相关
var DB_NAME='hermes_web_chat';
var DB_VERSION=1;
var STORE_NAME='chat_sessions';
var dbReady=false;

// 分页相关
var sessionPagination={currentPage:1,pageSize:10};

// Configure marked.js for better Markdown rendering with syntax highlighting
if(typeof marked!=='undefined'){
    // Configure marked options
    marked.setOptions({
        breaks:true,           // Convert \n to <br>
        gfm:true,              // GitHub Flavored Markdown
        headerIds:true,        // Add IDs to headers
        mangle:false,          // Don't escape header IDs
        sanitize:false,        // Don't sanitize HTML (allow custom styling)
        highlight: function(code, lang) {
            // Use highlight.js for syntax highlighting
            if(typeof hljs!=='undefined'){
                // Try to highlight with specified language
                if(lang && lang.trim()){
                    try {
                        // Check if language is registered
                        if(hljs.getLanguage(lang)){
                            return hljs.highlight(code, {language: lang}).value;
                        }
                    } catch(e) {
                        console.warn('Highlight error for language '+lang+':', e);
                    }
                }
                // Fallback to auto-detection
                try {
                    var result = hljs.highlightAuto(code);
                    return result.value;
                } catch(e) {
                    console.warn('Highlight auto error:', e);
                }
            }
            return code; // Return plain code if highlighting fails
        }
    });
}

// ========== Task list plugin for marked.js ==========
// ========== Task list post-processing ==========
// Instead of custom marked extension, convert task lists in HTML after parsing
function processTaskLists(html){
    // Match: <li>- [x] text</li> or <li>- [ ] text</li>
    return html.replace(/<li>(\s*)[-*+]\s*\[([ xX])\]\s*(.+?)<\/li>/gi, function(match, space, checked, content){
        var isChecked = checked.toLowerCase() === 'x' ? 'checked' : '';
        return '<div class="task-list-item" style="display:flex;align-items:center;gap:8px;margin:6px 0;"><input type="checkbox" disabled '+isChecked+' style="accent-color:var(--accent-primary);flex-shrink:0;width:16px;height:16px;"></input><span style="flex:1;">'+content+'</span></div>';
    });
}

// ========== Code block copy button ==========
function copyCodeBlocks(){
    if(typeof document==='undefined')return;
    var codeBlocks=document.querySelectorAll('.message-text pre');
    for(var i=0;i<codeBlocks.length;i++){
        var pre=codeBlocks[i];
        if(pre.querySelector('.code-copy-btn'))continue; // Already added
        var wrapper=document.createElement('div');
        wrapper.className='code-block-wrapper';
        pre.parentNode.insertBefore(wrapper,pre);
        wrapper.appendChild(pre);
        var btn=document.createElement('button');
        btn.className='code-copy-btn';
        btn.textContent='📋 复制';
        btn.onclick=(function(p){
            return function(e){
                e.stopPropagation();
                var code=p.querySelector('code');
                var text=code?code.textContent:p.textContent;
                navigator.clipboard.writeText(text).then(function(){
                    btn.textContent='✓ 已复制';
                    btn.classList.add('copied');
                    setTimeout(function(){btn.textContent='📋 复制';btn.classList.remove('copied');},2000);
                }).catch(function(){
                    // Fallback for older browsers
                    var ta=document.createElement('textarea');
                    ta.value=text;document.body.appendChild(ta);
                    ta.select();document.execCommand('copy');
                    document.body.removeChild(ta);
                    btn.textContent='✓ 已复制';
                    btn.classList.add('copied');
                    setTimeout(function(){btn.textContent='📋 复制';btn.classList.remove('copied');},2000);
                });
            };
        })(pre);
        wrapper.appendChild(btn);
        // Add language label if available
        var codeEl=pre.querySelector('code');
        if(codeEl&&codeEl.className){
            var langMatch=codeEl.className.match(/language-(\w+)/);
            if(langMatch){pre.setAttribute('data-language',langMatch[1]);}
        }
    }
}

// ========== KaTeX Math rendering ==========
function renderMath(container){
    if(typeof renderMathInElement==='undefined')return;
    try{
        renderMathInElement(container,{
            delimiters:[
                {left:'$$',right:'$$',display:true},
                {left:'$',right:'$',display:false},
                {left:'\\(',right:'\\)',display:false},
                {left:'\\[',right:'\\]',display:true}
            ],
            throwOnError:false
        });
    }catch(e){
        console.warn('KaTeX render error:',e);
    }
}

// ========== Apply post-render enhancements ==========
function enhanceMessage(container){
    copyCodeBlocks();
    renderMath(container);
}

// ========== IndexedDB 存储层 ==========

function openDB(callback){
    if(typeof indexedDB==='undefined'){
        console.warn('IndexedDB not available, falling back to localStorage');
        if(callback) callback();
        return;
    }
    try{
        var request=indexedDB.open(DB_NAME,DB_VERSION);
        request.onupgradeneeded=function(e){
            var db=e.target.result;
            if(!db.objectStoreNames.contains(STORE_NAME)){
                db.createObjectStore(STORE_NAME);
            }
        };
        request.onsuccess=function(e){
            dbReady=true;
            if(callback) callback();
        };
        request.onerror=function(e){
            console.error('IndexedDB open error:',e.target.error);
            if(callback) callback();
        };
    }catch(e){
        console.error('IndexedDB not supported:',e);
        if(callback) callback();
    }
}

function idbPut(key,value,callback){
    if(!dbReady||typeof indexedDB==='undefined'){
        if(callback) callback(false);
        return;
    }
    try{
        var dbRequest=indexedDB.open(DB_NAME,DB_VERSION);
        dbRequest.onsuccess=function(e){
            var db=e.target.result;
            var tx=db.transaction(STORE_NAME,'readwrite');
            var store=tx.objectStore(STORE_NAME);
            store.put(value,key);
            tx.oncomplete=function(){
                if(callback) callback(true);
            };
            tx.onerror=function(err){
                console.error('IndexedDB put error:',err);
                if(callback) callback(false);
            };
        };
        dbRequest.onerror=function(err){
            console.error('IndexedDB open for put error:',err);
            if(callback) callback(false);
        };
    }catch(e){
        console.error('IndexedDB put exception:',e);
        if(callback) callback(false);
    }
}

function idbGet(key,callback){
    if(!dbReady||typeof indexedDB==='undefined'){
        if(callback) callback(null);
        return;
    }
    try{
        var dbRequest=indexedDB.open(DB_NAME,DB_VERSION);
        dbRequest.onsuccess=function(e){
            var db=e.target.result;
            var tx=db.transaction(STORE_NAME,'readonly');
            var store=tx.objectStore(STORE_NAME);
            var getRequest=store.get(key);
            getRequest.onsuccess=function(){
                if(callback) callback(getRequest.result||null);
            };
            getRequest.onerror=function(){
                if(callback) callback(null);
            };
        };
        dbRequest.onerror=function(){
            if(callback) callback(null);
        };
    }catch(e){
        console.error('IndexedDB get exception:',e);
        if(callback) callback(null);
    }
}

function idbDelete(key,callback){
    if(!dbReady||typeof indexedDB==='undefined'){
        if(callback) callback(false);
        return;
    }
    try{
        var dbRequest=indexedDB.open(DB_NAME,DB_VERSION);
        dbRequest.onsuccess=function(e){
            var db=e.target.result;
            var tx=db.transaction(STORE_NAME,'readwrite');
            var store=tx.objectStore(STORE_NAME);
            store.delete(key);
            tx.oncomplete=function(){
                if(callback) callback(true);
            };
            tx.onerror=function(){
                if(callback) callback(false);
            };
        };
        dbRequest.onerror=function(){
            if(callback) callback(false);
        };
    }catch(e){
        if(callback) callback(false);
    }
}

function idbClear(callback){
    if(!dbReady||typeof indexedDB==='undefined'){
        if(callback) callback(false);
        return;
    }
    try{
        var dbRequest=indexedDB.open(DB_NAME,DB_VERSION);
        dbRequest.onsuccess=function(e){
            var db=e.target.result;
            var tx=db.transaction(STORE_NAME,'readwrite');
            var store=tx.objectStore(STORE_NAME);
            store.clear();
            tx.oncomplete=function(){
                if(callback) callback(true);
            };
            tx.onerror=function(){
                if(callback) callback(false);
            };
        };
        dbRequest.onerror=function(){
            if(callback) callback(false);
        };
    }catch(e){
        if(callback) callback(false);
    }
}

function idbGetAllKeys(callback){
    if(!dbReady||typeof indexedDB==='undefined'){
        if(callback) callback([]);
        return;
    }
    try{
        var dbRequest=indexedDB.open(DB_NAME,DB_VERSION);
        dbRequest.onsuccess=function(e){
            var db=e.target.result;
            var tx=db.transaction(STORE_NAME,'readonly');
            var store=tx.objectStore(STORE_NAME);
            var keys=[];
            var cursorRequest=store.openCursor();
            cursorRequest.onsuccess=function(e){
                var cursor=e.target.result;
                if(cursor){
                    keys.push(cursor.key);
                    cursor.continue();
                }else{
                    if(callback) callback(keys);
                }
            };
            cursorRequest.onerror=function(){
                if(callback) callback([]);
            };
        };
        dbRequest.onerror=function(){
            if(callback) callback([]);
        };
    }catch(e){
        if(callback) callback([]);
    }
}

// 迁移 localStorage 数据到 IndexedDB
function migrateLocalStorageToIndexedDB(callback){
    try{
        var migrated=false;
        var keysToMigrate=[];
        for(var k in localStorage){
            if(k.startsWith('hermes_chat_') && localStorage.hasOwnProperty(k)){
                keysToMigrate.push(k);
            }
        }
        if(keysToMigrate.length===0){
            if(callback) callback();
            return;
        }
        var pending=keysToMigrate.length;
        for(var i=0;i<keysToMigrate.length;i++){
            (function(key){
                var value=localStorage[key];
                try{
                    var parsed=JSON.parse(value);
                    idbPut(key,parsed,function(success){
                        if(success){
                            // 迁移成功后删除 localStorage 中的数据
                            localStorage.removeItem(key);
                            migrated=true;
                        }
                        pending--;
                        if(pending===0 && callback){
                            if(migrated) console.log('Migrated '+keysToMigrate.length+' sessions to IndexedDB');
                            callback();
                        }
                    });
                }catch(e){
                    pending--;
                    if(pending===0 && callback) callback();
                }
            })(keysToMigrate[i]);
        }
    }catch(e){
        if(callback) callback();
    }
}

// 安全版本的 localStorage 配额估算（不写入探测）
function getLocalStorageQuota(){
    // 保守估计 localStorage 可用空间为 5MB
    try {
        var used = 0;
        for (var k in localStorage) {
            if (localStorage.hasOwnProperty(k)) {
                used += new Blob([localStorage[k]]).size;
            }
        }
        return Math.max(0, 5242880 - used);
    } catch(e) { return 1048576; }
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

window.onload=function(){
    chatMessages=document.getElementById('chatMessages');
    messageInput=document.getElementById('messageInput');
    previewContainer=document.getElementById('previewContainer');
    previewImage=document.getElementById('previewImage');
    filePreviewContainer=document.getElementById('filePreviewContainer');
    sendBtn=document.getElementById('sendBtn');
    initMenu();
    setupInput();
    loadTheme();
    // 初始化 IndexedDB 并迁移数据
    openDB(function(){
        dbReady=true;
        migrateLocalStorageToIndexedDB(function(){
            loadChatHistory();
        });
    });
    // 添加键盘快捷键
    setupKeyboardShortcuts();
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

// 从消息内容提取更好的会话标题
function extractSessionTitle(){
    var msgs=chatMessages.querySelectorAll('.message.user');
    for(var i=0;i<msgs.length;i++){
        var textDiv=msgs[i].querySelector('.message-text');
        if(textDiv){
            var text=textDiv.textContent||textDiv.innerText||'';
            if(text.trim()){
                // 取前 30 个字符作为标题
                var title=text.trim().substring(0,30);
                if(title.length>=30) title+='...';
                return title;
            }
        }
    }
    return '新会话';
}

function createNewSession(){
    var now=new Date();
    var sessionName='session_'+now.getTime();
    CURRENT_SESSION=sessionName;
    chatMessages.innerHTML='';
    addMessage('✨ 新会话已创建！有什么可以帮你的吗？',false,null,false);
    document.getElementById('currentSessionTitle').textContent='💬 新会话';
}

function updateSessionTitle(){
    var title=CURRENT_SESSION.replace(/_/g,' ').replace('session ','');
    document.getElementById('currentSessionTitle').textContent='💬 '+title;
}

function switchSession(sessionId){
    // 尝试从当前会话的第一条用户消息提取标题
    var msgs=chatMessages.querySelectorAll('.message.user');
    if(msgs.length>0){
        var firstUserMsg=msgs[0];
        var textDiv=firstUserMsg.querySelector('.message-text');
        if(textDiv){
            var text=textDiv.textContent||textDiv.innerText||'';
            if(text.trim()){
                var title=text.trim().substring(0,30);
                if(title.length>=30) title+='...';
                document.getElementById('currentSessionTitle').textContent='💬 '+title;
            }
        }
    }
    CURRENT_SESSION=sessionId;
    loadChatHistory();
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
    messageInput.addEventListener('keydown',function(e){
        if(e.key==='Enter'&&!e.shiftKey){
            // 如果正在思考中，不发送消息
            if(isThinking){
                e.preventDefault();
                return;
            }
            e.preventDefault();
            sendMessage();
        }
    });
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
    // 优先从 IndexedDB 加载
    if(dbReady){
        idbGet(sessionKey,function(data){
            if(data){
                renderChatHistory(data);
            }else{
                // fallback: 尝试 localStorage
                try{
                    var saved=localStorage.getItem(sessionKey);
                    if(saved){
                        var history=JSON.parse(saved);
                        renderChatHistory(history);
                    }else{
                        chatMessages.innerHTML='';
                        addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
                    }
                }catch(e){
                    chatMessages.innerHTML='';
                    addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
                }
            }
        });
    }else{
        // IndexedDB 不可用，使用 localStorage
        try{
            var saved=localStorage.getItem(sessionKey);
            if(saved){
                var history=JSON.parse(saved);
                renderChatHistory(history);
            }else{
                chatMessages.innerHTML='';
                addMessage('👋 你好！我是 Hermes Agent，有什么可以帮你的吗？',false,null,false);
            }
        }catch(e){console.error('Load error:',e);}
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
            // 优化：如果图片是 base64 且较大，不存储
            var imgData=null;
            if(img){
                var src=img.src;
                // 如果是 base64 且超过 100KB，不存储
                if(src.startsWith('data:')&&src.length>102400){
                    imgData=null; // 不存储大图片
                    console.log('Skip storing large image');
                }else{
                    imgData=src;
                }
            }
            msgs.push({content:content,isUser:isUser,imageData:imgData});
        }
        if(msgs.length>100)msgs=msgs.slice(-100);
        var jsonData=JSON.stringify(msgs);

        // 优先使用 IndexedDB
        if(dbReady){
            idbPut(sessionKey,msgs,function(success){
                if(!success){
                    // IndexedDB 失败时回退到 localStorage
                    try{
                        if(willExceedQuota(sessionKey,jsonData)){
                            console.warn('Storage quota warning');
                            for(var j=0;j<msgs.length;j++)msgs[j].imageData=null;
                            jsonData=JSON.stringify(msgs);
                        }
                        localStorage.setItem(sessionKey,jsonData);
                    }catch(e){
                        console.error('Save error:',e);
                    }
                }
            });
        }else{
            // IndexedDB 不可用，使用 localStorage
            if(willExceedQuota(sessionKey,jsonData)){
                console.warn('LocalStorage quota warning, storing without images');
                for(var j=0;j<msgs.length;j++){
                    msgs[j].imageData=null;
                }
                jsonData=JSON.stringify(msgs);
            }
            localStorage.setItem(sessionKey,jsonData);
        }
    }catch(e){
        console.error('Save error:',e);
    }
}

// 清理 7 天前的旧会话
function clearOldSessions(){
    try{
        var now=new Date();
        var cutoff=new Date(now.getTime()-7*24*60*60*1000); // 7 天前

        // 清理 IndexedDB 中的旧会话
        if(dbReady){
            idbGetAllKeys(function(keys){
                for(var i=0;i<keys.length;i++){
                    if(keys[i].startsWith('hermes_chat_session_')){
                        var dateStr=keys[i].replace('hermes_chat_session_','').substring(0,8);
                        if(dateStr.length===8){
                            var year=parseInt(dateStr.substring(0,4));
                            var month=parseInt(dateStr.substring(4,6))-1;
                            var day=parseInt(dateStr.substring(6,8));
                            var sessionDate=new Date(year,month,day);
                            if(sessionDate<cutoff){
                                idbDelete(keys[i],null);
                                console.log('Removed old session from IndexedDB:',keys[i]);
                            }
                        }
                    }
                }
            });
        }

        // 清理 localStorage 中的旧会话（fallback）
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
            console.log('Removed old session from localStorage:',keysToRemove[i]);
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
    var renderedContent=isUser?escapeHtml(content).split('\n').join('<br>'):processTaskLists(marked.parse(content));
    var html='<div class="message-avatar">'+(isUser?'👤':'🤖')+'</div><div class="message-content"><div class="message-text">'+renderedContent+'</div>';
    if(imageData)html+='<img class="message-image" src="'+imageData+'">';
    html+='</div>';
    div.innerHTML=html;
    if(isUser){div.style.cursor='pointer';div.title='右键点击重新编辑';div.oncontextmenu=function(e){e.preventDefault();editMessage(this);};}
    chatMessages.appendChild(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    if(!isUser) enhanceMessage(div);
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
    textDiv.innerHTML=processTaskLists(marked.parse(content));
    enhanceMessage(div);
    chatMessages.scrollTop=chatMessages.scrollHeight;
    saveChatHistory();
}

function sendMessage(){
    // 如果正在思考中，点击按钮则停止生成
    if(isThinking){
        stopGeneration();
        return;
    }
    
    var message=messageInput.value.trim();
    if(!message&&!currentImage&&!currentFile)return;
    
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
function stopGeneration(){
    if(currentXhr){
        currentXhr.abort();
        currentXhr=null;
    }
    isThinking=false;
    sendBtn.innerHTML='⬆️';
    sendBtn.title='发送';
    sendBtn.classList.remove('thinking');
    sendBtn.disabled=false;
    messageInput.focus();
    // 移除加载框
    removeLoading();
    // 添加停止提示
    var lastAssistantMsg=chatMessages.querySelector('.message.assistant:last-child');
    if(lastAssistantMsg){
        var textDiv=lastAssistantMsg.querySelector('.message-text');
        var raw=lastAssistantMsg.rawMarkdown||textDiv.textContent;
        if(raw && raw.trim()){
            // 已有内容，追加停止提示
            textDiv.innerHTML=processTaskLists(marked.parse(raw+'\n\n*▎已停止生成*'));
        }else if(textDiv){
            // 还没有内容，显示停止提示
            textDiv.innerHTML=processTaskLists(marked.parse('*▎已停止生成*'));
        }
    }
    saveChatHistory();
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
    var firstContent=true;
    var rawMarkdown='';
    
    // 创建新的 XHR 请求
    var xhr=new XMLHttpRequest();
    currentXhr=xhr;  // 保存当前请求
    isThinking=true;  // 标记为思考中
    sendBtn.innerHTML='⏸️';  // 更改为暂停图标
    sendBtn.title='停止生成';
    sendBtn.classList.add('thinking');
    
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
                    // 请求完成，统一渲染 Markdown
                    if(assistantDiv && textDiv){
                        textDiv.innerHTML=processTaskLists(marked.parse(assistantDiv.rawMarkdown));
                    }
                    // 请求完成，增强渲染（代码复制、KaTeX）
                    if(assistantDiv) enhanceMessage(assistantDiv);
                    // 请求完成
                    isThinking=false;
                    currentXhr=null;
                    sendBtn.innerHTML='⬆️';
                    sendBtn.title='发送';
                    sendBtn.classList.remove('thinking');
                    sendBtn.disabled=false;
                    messageInput.focus();
                    saveChatHistory();
                    return;
                }
                if(data==='') continue;
                if(firstContent){
                    // 第一次收到回复时，创建助手消息框
                    removeLoading();
                    assistantDiv=createAssistantMessage();
                    textDiv=assistantDiv.querySelector('.message-text');
                    firstContent=false;
                }
                // 流式追加：实时显示纯文本（不渲染 Markdown）
                if(data.trim()){
                    assistantDiv.rawMarkdown+=data+'\n';
                    // 实时显示纯文本内容，让用户看到进度
                    textDiv.textContent=assistantDiv.rawMarkdown;
                    chatMessages.scrollTop=chatMessages.scrollHeight;
                }
            }
        }
    };
    
    xhr.onload=function(){
        if(xhr.status!==200){
            if(textDiv) textDiv.innerHTML=processTaskLists(marked.parse(assistantDiv.rawMarkdown+'\n\n**[发送失败]**'));
        }
        // 请求完成，重置状态（如果未被中止）
        if(isThinking){
            isThinking=false;
            currentXhr=null;
            sendBtn.innerHTML='⬆️';
            sendBtn.title='发送';
            sendBtn.classList.remove('thinking');
        }
        sendBtn.disabled=false;
        messageInput.focus();
        saveChatHistory();
    };
    
    xhr.onerror=function(){
        // 如果是被中止的，不显示错误
        if(xhr.statusText==='abort'){
            return;
        }
        if(textDiv) textDiv.innerHTML=processTaskLists(marked.parse(assistantDiv.rawMarkdown+'\n\n**[网络错误]**'));
        isThinking=false;
        currentXhr=null;
        sendBtn.innerHTML='⬆️';
        sendBtn.title='发送';
        sendBtn.classList.remove('thinking');
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
    div.rawMarkdown='';
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
function clearChatHistory(){
    if(confirm('确定清空当前对话？')){
        var sessionKey='hermes_chat_'+CURRENT_SESSION;
        if(dbReady){
            idbDelete(sessionKey,function(){
                chatMessages.innerHTML='';
                addMessage('对话已清空',false,null,false);
            });
        }else{
            localStorage.removeItem(sessionKey);
            chatMessages.innerHTML='';
            addMessage('对话已清空',false,null,false);
        }
    }
}

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
    sessionPagination.currentPage=1;
    renderList.currentPage='sessions';
    fetch('/api/sessions').then(function(r){return r.json();}).then(function(data){
        allSessionsData=data;
        renderList(data);
    });
}
function filterSessions(){
    var days=document.getElementById('sessionDateFilter').value;
    if(days==='all'){sessionPagination.currentPage=1;renderList(allSessionsData);return;}
    var cutoff=new Date();
    cutoff.setDate(cutoff.getDate()-parseInt(days));
    var filtered={sessions:allSessionsData.sessions.filter(function(s){
        var d=new Date(s.created||'');
        return d>=cutoff;
    })};
    sessionPagination.currentPage=1;
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
    var page=renderList.currentPage||'memory';
    var html='';

    if(data.skills){
        html+='<div class="card"><ul class="data-list">';
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
        html+='</ul></div>';
    }
    else if(data.sessions){
        html+='<div class="card"><ul class="data-list">';
        var sessions=data.sessions;
        if(sessions.length===0){
            html+='<li style="color:#666;text-align:center;padding:20px;">暂无会话数据</li>';
        }else{
            // 分页处理
            var totalSessions=sessions.length;
            var pageSize=sessionPagination.pageSize;
            var totalPages=Math.ceil(totalSessions/pageSize);
            var startIdx=(sessionPagination.currentPage-1)*pageSize;
            var endIdx=Math.min(startIdx+pageSize,totalSessions);
            var pageSessions=sessions.slice(startIdx,endIdx);

            for(var i=0;i<pageSessions.length;i++){
                var s=pageSessions[i];
                var SQ=String.fromCharCode(39);
                var DQ=String.fromCharCode(34);
                var safeTitle=String(s.title||'未命名').replace(new RegExp(SQ,'g'),'\\x27').replace(new RegExp(DQ,'g'),'\\x22');
                html+='<li class="session-item" data-session-id="'+s.id+'" data-session-title="'+safeTitle+'" style="cursor:pointer;">';
                html+='<strong>'+(s.title||'未命名')+'</strong><br>';
                html+='<small>'+(s.created||'')+' | '+s.messages+' 条</small>';
                html+='</li>';
            }

            // 分页控件
            html+='</ul>';
            if(totalPages>1){
                html+='<div class="pagination" style="display:flex;justify-content:center;align-items:center;gap:12px;padding:10px 0;">';
                if(sessionPagination.currentPage>1){
                    html+='<button onclick="sessionPagination.currentPage--;renderList(allSessionsData);" style="background:#00d9ff;color:#0f0f1a;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;">上一页</button>';
                }else{
                    html+='<span style="color:#666;">上一页</span>';
                }
                html+='<span style="color:#aaa;font-size:13px;">第 '+sessionPagination.currentPage+' / '+totalPages+' 页 (共 '+totalSessions+' 条)</span>';
                if(sessionPagination.currentPage<totalPages){
                    html+='<button onclick="sessionPagination.currentPage++;renderList(allSessionsData);" style="background:#00d9ff;color:#0f0f1a;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;">下一页</button>';
                }else{
                    html+='<span style="color:#666;">下一页</span>';
                }
                html+='</div>';
            }
            html+='</div>';
            var contentDiv=document.getElementById(page+'-content');
            contentDiv.innerHTML=html;
            // 绑定会话点击事件
            var items=contentDiv.querySelectorAll('.session-item');
            for(var i=0;i<items.length;i++){
                items[i].onclick=function(){
                    var sessionId=this.getAttribute('data-session-id');
                    var sessionTitle=this.getAttribute('data-session-title');
                    openSession(sessionId,sessionTitle);
                };
            }
            return;
        }
        html+='</ul></div>';
    }
    else if(data.projects||data.daily){
        html+='<div class="card"><ul class="data-list">';
        var items=data.projects||data.daily;
        if(items && items.length>0){
            for(var i=0;i<items.length;i++)html+='<li>'+items[i]+'</li>';
        }else{
            html+='<li style="color:#666;text-align:center;padding:20px;">暂无数据</li>';
        }
        html+='</ul></div>';
    }
    else if(data.skills!==undefined && data.skills.length===0){
        html+='<div class="card"><ul class="data-list"><li style="color:#666;text-align:center;padding:20px;">暂无技能数据</li></ul></div>';
    }
    else if(data.sessions!==undefined && data.sessions.length===0){
        html+='<div class="card"><ul class="data-list"><li style="color:#666;text-align:center;padding:20px;">暂无会话数据</li></ul></div>';
    }
    else{html+='<div class="card"><ul class="data-list"><li>暂无数据</li></ul></div>';}

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

    // 先尝试从 IndexedDB 加载
    if(dbReady){
        idbGet(sessionKey,function(data){
            if(data){
                renderChatHistory(data);
                return;
            }
            // IndexedDB 没有，尝试 localStorage
            try{
                var saved=localStorage.getItem(sessionKey);
                if(saved){
                    var history=JSON.parse(saved);
                    renderChatHistory(history);
                    return;
                }
            }catch(e){}
            // 从服务器加载历史会话
            fetchSessionFromServer(sessionKey);
        });
    }else{
        // 先尝试从 localStorage 加载
        var saved=localStorage.getItem(sessionKey);
        if(saved){
            try{
                var history=JSON.parse(saved);
                renderChatHistory(history);
                return;
            }catch(e){}
        }
        // 从服务器加载历史会话
        fetchSessionFromServer(sessionKey);
    }
}

function fetchSessionFromServer(sessionKey){
    fetch('/api/session_detail?session_id='+encodeURIComponent(CURRENT_SESSION))
        .then(function(r){return r.json();})
        .then(function(data){
            if(data.messages && data.messages.length>0){
                renderChatHistory(data.messages);
                // 存储到 IndexedDB（优先）或 localStorage
                var msgsToStore=[];
                for(var i=0;i<data.messages.length;i++){
                    var msg=data.messages[i];
                    if(msg.imageData && msg.imageData.startsWith('data:') && msg.imageData.length>102400){
                        msgsToStore.push({content:msg.content,isUser:msg.isUser,imageData:null});
                    }else{
                        msgsToStore.push(msg);
                    }
                }
                if(dbReady){
                    idbPut(sessionKey,msgsToStore,null);
                }else{
                    try{
                        var jsonData=JSON.stringify(msgsToStore);
                        if(willExceedQuota(sessionKey,jsonData)){
                            for(var j=0;j<msgsToStore.length;j++){
                                msgsToStore[j].imageData=null;
                            }
                            jsonData=JSON.stringify(msgsToStore);
                        }
                        localStorage.setItem(sessionKey,jsonData);
                    }catch(e){
                        console.error('Save server session error:',e);
                    }
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
        var renderedContent=msg.isUser?escapeHtml(msg.content).split(NL).join('<br>'):processTaskLists(marked.parse(msg.content));
        var html='<div class="message-avatar">'+(msg.isUser?'👤':'🤖')+'</div><div class="message-content"><div class="message-text">'+renderedContent+'</div>';
        if(msg.imageData)html+='<img class="message-image" src="'+msg.imageData+'">';
        html+='</div>';
        div.innerHTML=html;
        if(msg.isUser){div.style.cursor='pointer';div.title='右键点击重新编辑';div.oncontextmenu=function(e){e.preventDefault();editMessage(this);};}
        chatMessages.appendChild(div);
        if(!msg.isUser) enhanceMessage(div);
    }
    chatMessages.scrollTop=chatMessages.scrollHeight;
}

// 解析 cron 数据为结构化表格
function renderRaw(data){
    var html='';
    var page=renderRaw.currentPage||'cron';
    var contentDiv=document.getElementById(page+'-content');

    if(page==='cron' && data.raw){
        var raw=data.raw;
        // 尝试解析 cronjob list 输出为结构化表格
        if(raw.includes('ID') && raw.includes('SCHEDULE') || raw.includes('COMMAND')){
            // 检测到可能是 cronjob list 格式，尝试解析
            var lines=raw.split('\n');
            var entries=[];
            var header=null;

            for(var i=0;i<lines.length;i++){
                var line=lines[i].trim();
                if(!line) continue;

                if(!header){
                    // 尝试识别表头行
                    if(line.match(/^ID[\s]+|^\s*ID\s/) || line.match(/COMMAND/)){
                        header=line;
                        continue;
                    }
                    // 如果第一行不是表头，可能没有表头
                    continue;
                }

                // 解析数据行 - 尝试多种格式
                var match=null;
                // 格式: ID    SCHEDULE    STATUS    COMMAND
                match=line.match(/^(\d+)\s+(.+?)\s+(\w+)\s+(.+)$/);
                if(match){
                    entries.push({id:match[1],schedule:match[2],status:match[3],command:match[4]});
                    continue;
                }
                // 格式: ID    SCHEDULE    COMMAND  (无状态)
                match=line.match(/^(\d+)\s+(.+?)\s{2,}(.+)$/);
                if(match){
                    entries.push({id:match[1],schedule:match[2],status:'',command:match[3]});
                    continue;
                }
                // 其他格式，保留原始行
                entries.push({id:'',schedule:'',status:'',command:line});
            }

            if(entries.length>0){
                html+='<div class="card"><h3 style="color:#00d9ff;margin-bottom:15px;">📋 Cron 任务列表</h3>';
                html+='<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;">';
                html+='<thead><tr style="border-bottom:2px solid #00d9ff;">';
                html+='<th style="text-align:left;padding:8px 12px;color:#00d9ff;">ID</th>';
                html+='<th style="text-align:left;padding:8px 12px;color:#00d9ff;">SCHEDULE</th>';
                html+='<th style="text-align:left;padding:8px 12px;color:#00d9ff;">STATUS</th>';
                html+='<th style="text-align:left;padding:8px 12px;color:#00d9ff;">COMMAND</th>';
                html+='</tr></thead><tbody>';
                for(var j=0;j<entries.length;j++){
                    var e=entries[j];
                    var statusColor=e.status==='active'?'#00ff88':e.status==='paused'?'#ffaa00':'#aaa';
                    html+='<tr style="border-bottom:1px solid #1a1a2e;">';
                    html+='<td style="padding:8px 12px;color:#00d9ff;">'+escapeHtml(e.id)+'</td>';
                    html+='<td style="padding:8px 12px;"><code style="background:#0f0f1a;padding:2px 6px;border-radius:4px;">'+escapeHtml(e.schedule)+'</code></td>';
                    html+='<td style="padding:8px 12px;color:'+statusColor+';">'+escapeHtml(e.status)+'</td>';
                    html+='<td style="padding:8px 12px;font-family:monospace;">'+escapeHtml(e.command)+'</td>';
                    html+='</tr>';
                }
                html+='</tbody></table></div>';
                html+='<p style="color:#666;font-size:12px;margin-top:10px;">共 '+entries.length+' 个任务</p></div>';
                contentDiv.innerHTML=html;
                return;
            }
        }
        // 如果无法解析为结构化数据，显示原始文本
        html='<div class="card"><pre style="background:#0f0f1a;padding:15px;border-radius:8px;white-space:pre-wrap;overflow-x:auto;">'+escapeHtml(raw||'暂无数据')+'</pre></div>';
    }else{
        html='<div class="card"><pre style="background:#0f0f1a;padding:15px;border-radius:8px;white-space:pre-wrap;overflow-x:auto;">'+escapeHtml(data.raw||'暂无数据')+'</pre></div>';
    }
    contentDiv.innerHTML=html;
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
    var savedTheme=localStorage.getItem('hermes_theme');
    if(savedTheme){
        applyTheme(savedTheme);
    }else{
        // 系统主题自动检测
        if(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches){
            applyTheme('dark');
        }else{
            applyTheme('light');
        }
    }
    // 监听系统主题变化
    if(window.matchMedia){
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(e){
            if(!localStorage.getItem('hermes_theme')){
                applyTheme(e.matches?'dark':'light');
            }
        });
    }
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
        // 如果 IndexedDB 可用，也显示 IndexedDB 信息
        if(dbReady){
            idbGetAllKeys(function(keys){
                var idbCount=0;
                for(var i=0;i<keys.length;i++){
                    if(keys[i].startsWith('hermes_chat_'))idbCount++;
                }
                var sizeStr=totalSize<1024?totalSize+' B':(totalSize<1048576?(totalSize/1024).toFixed(1)+' KB':(totalSize/1048576).toFixed(2)+' MB');
                var infoDiv=document.getElementById('storageInfo');
                if(infoDiv){
                    infoDiv.innerHTML='📊 IndexedDB 会话：<strong>'+idbCount+'</strong> | localStorage 使用：<strong>'+sizeStr+'</strong> | localStorage 会话：<strong>'+sessionCount+'</strong>';
                }
            });
        }else{
            var sizeStr=totalSize<1024?totalSize+' B':(totalSize<1048576?(totalSize/1024).toFixed(1)+' KB':(totalSize/1048576).toFixed(2)+' MB');
            var infoDiv=document.getElementById('storageInfo');
            if(infoDiv){
                infoDiv.innerHTML='📊 当前使用：<strong>'+sizeStr+'</strong> | 会话数：<strong>'+sessionCount+'</strong>';
            }
        }
    }catch(e){
        console.error('Display storage info error:',e);
    }
}

// 清理所有本地会话数据
function clearAllLocalStorage(){
if(!confirm('确定要清理所有本地会话数据吗？\n\n注意：\n1. 这将删除所有保存在浏览器的聊天记录\n2. 服务器上的会话历史不会受影响\n3. 当前会话也会被清空\n\n此操作不可恢复！')){
        return;
    }
    var cleared=0;
    try{
        // 清理 IndexedDB
        if(dbReady){
            idbGetAllKeys(function(keys){
                for(var i=0;i<keys.length;i++){
                    if(keys[i].startsWith('hermes_chat_')){
                        idbDelete(keys[i],null);
                        cleared++;
                    }
                }
                finishClear(cleared);
            });
        }else{
            finishClear(0);
        }
    }catch(e){
        finishClear(cleared);
    }

    // 清理 localStorage
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
        cleared+=keysToRemove.length;
    }catch(e){}

    function finishClear(count){
        // 清空当前聊天界面
        chatMessages.innerHTML='';
        addMessage('🗑️ 本地会话数据已清理',false,null,false);
        displayStorageInfo();
        alert('已清理 '+count+' 个会话数据');
    }
}

// 插件更新功能
function checkForUpdates(){
    var statusEl=document.getElementById('updateStatus');
    var infoDiv=document.getElementById('updateInfo');
    var outputDiv=document.getElementById('updateOutput');
    var updateBtn=document.getElementById('updateNowBtn');
    
    statusEl.textContent='正在检查更新...';
    infoDiv.style.display='none';
    outputDiv.style.display='none';
    updateBtn.style.display='none';
    
    fetch('/api/plugin/update/check')
        .then(function(res){return res.json();})
        .then(function(data){
            if(data.error){
                statusEl.textContent='❌ '+data.error;
                return;
            }
            
            infoDiv.style.display='block';
            document.getElementById('currentVersion').textContent=data.current_version||'unknown';
            document.getElementById('latestVersion').textContent=data.latest_version||'unknown';
            
            if(data.has_update){
                statusEl.textContent='✅ 发现新版本！';
                document.getElementById('commitsBehind').textContent='落后 '+data.commits_behind+' 个提交';
                updateBtn.style.display='inline-block';
            }else{
                statusEl.textContent='✅ 已是最新版本';
                document.getElementById('commitsBehind').textContent='';
                updateBtn.style.display='none';
            }
        })
        .catch(function(err){
            statusEl.textContent='❌ 检查失败：'+err.message;
            console.error('Check update error:',err);
        });
}

function executeUpdate(){
    var statusEl=document.getElementById('updateStatus');
    var outputDiv=document.getElementById('updateOutput');
    var updateBtn=document.getElementById('updateNowBtn');
    var checkBtn=document.getElementById('checkUpdateBtn');
    
    if(!confirm('确定要更新插件吗？\n\n更新过程需要：\n1. 拉取最新代码\n2. 安装依赖\n3. 建议重启服务\n\n继续？')){
        return;
    }
    
    statusEl.textContent='🔄 正在更新...';
    outputDiv.style.display='block';
    outputDiv.innerHTML='正在拉取最新代码...<br>';
    updateBtn.disabled=true;
    checkBtn.disabled=true;
    
    fetch('/api/plugin/update/execute',{method:'POST'})
        .then(function(res){return res.json();})
        .then(function(data){
            if(data.success){
                statusEl.textContent='✅ 更新成功！';
                outputDiv.innerHTML+='<br><strong style="color:#00ff00;">'+data.message+'</strong><br><pre>'+data.output+'</pre>';
                alert('更新成功！\n\n'+data.message+'\n\n请重启服务以应用更改。');
            }else{
                statusEl.textContent='❌ 更新失败';
                outputDiv.innerHTML+='<br><strong style="color:#ff4444;">'+data.message+'</strong><br><pre>'+data.error+'</pre>';
                alert('更新失败：'+data.message+'\n\n'+data.error);
            }
        })
        .catch(function(err){
            statusEl.textContent='❌ 更新失败：'+err.message;
            outputDiv.innerHTML+='<br><strong style="color:#ff4444;">请求失败</strong><br><pre>'+err.message+'</pre>';
            alert('更新请求失败：'+err.message);
        })
        .finally(function(){
            updateBtn.disabled=false;
            checkBtn.disabled=false;
        });
}

// 键盘快捷键支持
function setupKeyboardShortcuts(){
    document.addEventListener('keydown',function(e){
        // Ctrl+K / Cmd+K: 新建会话
        if((e.ctrlKey||e.metaKey) && e.key==='k'){
            e.preventDefault();
            createNewSession();
            return;
        }
        // Ctrl+/: 聚焦输入框
        if((e.ctrlKey||e.metaKey) && e.key==='/'){
            e.preventDefault();
            messageInput.focus();
            return;
        }
        // Ctrl+L: 清空聊天
        if((e.ctrlKey||e.metaKey) && e.key==='l'){
            e.preventDefault();
            clearChatHistory();
            return;
        }
        // Escape: 停止生成
        if(e.key==='Escape' && isThinking){
            e.preventDefault();
            stopGeneration();
            return;
        }
    });
}
