import os
import time
import json
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import google.generativeai as gemini
from google.generativeai.types import GenerationConfig

# 設置log
def setup_logger(folder_path):
    log_file_path = os.path.join(folder_path, 'agent.log')

    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # 創建文件處理器 (FileHandler)，並設置其寫入文件的路徑
    # 在這裡加上 encoding='utf-8' 來確保能處理中文字符
    handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 使用者操作紀錄 ------------------------------------------------------
def driver_config():
    options = webdriver.ChromeOptions()
    options.add_experimental_option(
        "prefs", {
            "plugins.always_open_pdf_externally": True
        }
    )
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("disable-blink-features=AutomationControlled")
    return options

def inject_script(driver_task):
    driver_task.execute_script("""
        (function() {
            function setupUserInteractionListener() {
                if (window.__userInteractionInjected__ && window.__lastInjectedBody__ === document.body) {
                    console.log('[INFO] Script already injected, skipping.');
                    return;
                }
                console.log('[INFO] Injecting interaction listeners.');
                
                // 移除舊監聽器
                ['click', 'input', 'scroll', 'popstate', 'pageshow', 'beforeunload', 'okPrompt'].forEach(type => {
                    let listener = window[`__${type}Listener`];
                    if (listener) {
                        if (type === 'popstate' || type === 'pageshow') {
                            window.removeEventListener(type, listener);
                        } else {
                            document.removeEventListener(type, listener, true);
                        }
                        console.log(`[INFO] Removed existing ${type} listener.`);
                    }
                });

                window.__userInteractionInjected__ = true;
                window.__lastInjectedBody__ = document.body;

                window.userInteractions = JSON.parse(sessionStorage.getItem('userInteractions') || '[]');
                let lastRecordedValue = '';
                let lastClickTimestamp = 0;
                window.__processingPopstate__ = false;
                let lastScrollY = window.scrollY;

                const clickListener = function(event) {
                    if (event.__processed__) return;
                    const now = new Date().getTime();
                    if (now - lastClickTimestamp < 50) return;
                    lastClickTimestamp = now;
                    event.__processed__ = true;

                    let target = event.target.closest('a, img, [onclick], [data-nav], [role="option"], li, div, span') || event.target;
                    let rect = target.getBoundingClientRect();
                    let interaction = {
                        type: 'click',
                        target: target.tagName,
                        id: target.id,
                        class: target.className,
                        text: (target.innerText || target.value || '').slice(0, 100),
                        x: event.clientX,
                        y: event.clientY
                    };

                    const currentUrl = window.location.href.split('#')[0];
                    const targetUrl = (target.href || '').split('#')[0];

                    if (target.tagName.toLowerCase() === 'a' && target.href) {
                        if (currentUrl === targetUrl) {
                            window.userInteractions.push(interaction);
                            sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                        } else {
                            event.preventDefault();
                            window.userInteractions.push(interaction);
                            sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                            let clicks = JSON.parse(localStorage.getItem('navigationClicks') || '[]');
                            clicks.push(interaction);
                            localStorage.setItem('navigationClicks', JSON.stringify(clicks));
                            setTimeout(() => {
                                window.location.href = target.href;
                            }, 300);
                        }
                    } else if (target.closest('form') && window.location.href.includes('google.com')) {
                        window.userInteractions.push(interaction);
                        sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                        event.preventDefault();
                        setTimeout(() => {
                            target.closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                        }, 300);
                    } else {
                        window.userInteractions.push(interaction);
                        sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                    }
                };
                window.__clickListener = clickListener;
                document.addEventListener('click', clickListener, true);

                // 添加對綠框覆蓋層的點擊監聽
                const okPromptListener = function(event) {
                    if (event.target.id === 'ok_prompt_overlay') {
                        window.exitInteractionLoop = true;
                        event.stopPropagation();
                    }
                };
                window.__okPromptListener = okPromptListener;
                document.addEventListener('click', okPromptListener, true);

                const inputListener = function(event) {
                    if ((event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') && event.target.value !== lastRecordedValue) {
                        lastRecordedValue = event.target.value;
                        let interaction = {
                            type: 'input',
                            value: event.target.value.slice(0, 100),
                            target: event.target.tagName,
                            id: event.target.id,
                            class: event.target.className
                        };
                        window.userInteractions.push(interaction);
                        sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                    }
                };
                window.__inputListener = inputListener;
                document.addEventListener('input', inputListener, true);

                const scrollListener = function() {
                    if (window.scrollY !== lastScrollY) {
                        let interaction = {
                            type: 'scroll',
                            scrollY: window.scrollY
                        };
                        window.userInteractions.push(interaction);
                        sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                        lastScrollY = window.scrollY;
                    }
                };
                window.__scrollListener = scrollListener;
                window.addEventListener('scroll', scrollListener);

                const popstateListener = function(event) {
                    if (window.__processingPopstate__) {
                        console.log('[INFO] Ignoring popstate event during processing.');
                        return;
                    }
                    window.__processingPopstate__ = true;
                    let interaction = {
                        type: 'navigation',
                        action: 'back',
                        url: window.location.href
                    };
                    // 避免重複記錄
                    if (!window.userInteractions.some(i => i.type === 'navigation' && i.url === interaction.url && Math.abs(new Date(i.timestamp) - new Date(interaction.timestamp)) < 100)) {
                        window.userInteractions.push(interaction);
                        sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                        localStorage.setItem('pendingPopstateInteraction', JSON.stringify(interaction));
                        console.log('[INFO] Popstate interaction stored:', interaction);
                    }
                    setTimeout(() => {
                        window.__userInteractionInjected__ = false;
                        setupUserInteractionListener();
                        window.__processingPopstate__ = false;
                    }, 300);
                };
                window.__popstateListener = popstateListener;
                window.addEventListener('popstate', popstateListener);

                const pageshowListener = function(event) {
                    if (event.persisted) {
                        console.log('[INFO] Page restored from bfcache, reinjecting.');
                        let interaction = {
                            type: 'navigation',
                            action: 'back',
                            url: window.location.href
                        };
                        // 避免重複記錄
                        if (!window.userInteractions.some(i => i.type === 'navigation' && i.url === interaction.url && Math.abs(new Date(i.timestamp) - new Date(interaction.timestamp)) < 100)) {
                            window.userInteractions.push(interaction);
                            sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                            localStorage.setItem('pendingPopstateInteraction', JSON.stringify(interaction));
                            console.log('[INFO] Pageshow interaction stored:', interaction);
                        }
                        window.__userInteractionInjected__ = false;
                        setTimeout(() => {
                            setupUserInteractionListener();
                        }, 300);
                    }
                };
                window.__pageshowListener = pageshowListener;
                window.addEventListener('pageshow', pageshowListener);

                const beforeunloadListener = function() {
                    sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                    localStorage.setItem('navigationClicks', JSON.stringify([]));
                };
                window.__beforeunloadListener = beforeunloadListener;
                window.addEventListener('beforeunload', beforeunloadListener);

                (function recoverNavigation() {
                    const navClicks = JSON.parse(localStorage.getItem('navigationClicks') || '[]');
                    const pendingPopstate = JSON.parse(localStorage.getItem('pendingPopstateInteraction') || 'null');
                    const currentUrl = window.location.href;
                    if (pendingPopstate && pendingPopstate.url !== currentUrl) {
                        window.userInteractions.push(pendingPopstate);
                        sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                        localStorage.removeItem('pendingPopstateInteraction');
                    }
                    if (navClicks.length > 0) {
                        const lastClick = navClicks.pop();
                        window.userInteractions.push(lastClick);
                        sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
                        localStorage.setItem('navigationClicks', JSON.stringify(navClicks));
                    }
                })();
            }

            function monkeyPatchHistoryMethod(methodName) {
                const original = history[methodName];
                history[methodName] = function() {
                    const result = original.apply(this, arguments);
                    setTimeout(() => {
                        window.__userInteractionInjected__ = false;
                        setupUserInteractionListener();
                    }, 300);
                    return result;
                };
            }

            setupUserInteractionListener();
            monkeyPatchHistoryMethod('pushState');
            monkeyPatchHistoryMethod('replaceState');

            window.addEventListener('load', function() {
                setTimeout(() => {
                    window.__userInteractionInjected__ = false;
                    setupUserInteractionListener();
                }, 300);
            });

            const observer = new MutationObserver(() => {
                if (window.__lastInjectedBody__ !== document.body) {
                    window.__userInteractionInjected__ = false;
                    setupUserInteractionListener();
                }
            });
            observer.observe(document.documentElement, { childList: true, subtree: true });
        })();
    """)

def safe_inject(driver_task):
    while True:
        try:
            # 等待頁面載入完成
            WebDriverWait(driver_task, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            injected = driver_task.execute_script("return window.__userInteractionInjected__ === true;")
            if not injected:
                inject_script(driver_task)
            break
        except Exception as e:
            logging.warning(f"Failed to inject script: {e}")
            time.sleep(2.5)

def get_user_interactions(driver_task):
    """ 從 Selenium 瀏覽器取得使用者互動紀錄 """
    try:
        interactions = driver_task.execute_script("return window.userInteractions || [];")
    except Exception as e:
        logging.warning(f"Failed to get user interactions: {e}")
        return []

    return interactions

def clear_userInteractions(driver_task):
    try:
        script = """
        window.userInteractions = [];
        sessionStorage.setItem('userInteractions', JSON.stringify(window.userInteractions));
        localStorage.setItem('navigationClicks', JSON.stringify([]));
        """
        driver_task.execute_script(script)
    except Exception as e:
        logging.warning(f"Failed to reset user interactions: {e}")

def inject_ok_prompt(driver):
    """
    注入 JavaScript 腳本，為整個網頁介面添加綠色外框，並添加四個覆蓋層用於檢測邊框點擊。
    外框和覆蓋層都使用固定定位，確保它們不會隨著頁面滾動而移動。
    
    Args:
        driver: Selenium WebDriver 實例
    """
    js_script = """
    (function() {
        // 移除現有的邊框和覆蓋層
        document.body.style.border = '';
        ['top', 'bottom', 'left', 'right'].forEach(function(side) {
            var existingOverlay = document.getElementById('ok_prompt_overlay_' + side);
            if (existingOverlay) {
                existingOverlay.remove();
            }
        });

        // 移除舊的邊框容器（如果存在）
        var existingBorderContainer = document.getElementById('ok_prompt_border_container');
        if (existingBorderContainer) {
            existingBorderContainer.remove();
        }

        // 創建一個固定定位的邊框容器
        var borderContainer = document.createElement('div');
        borderContainer.id = 'ok_prompt_border_container';
        borderContainer.style.position = 'fixed';
        borderContainer.style.top = '0';
        borderContainer.style.left = '0';
        borderContainer.style.width = '100%';
        borderContainer.style.height = '100%';
        borderContainer.style.border = '5px solid #28a745';
        borderContainer.style.boxSizing = 'border-box';
        borderContainer.style.pointerEvents = 'none'; // 確保邊框本身不攔截點擊事件
        borderContainer.style.zIndex = '9998'; // 設置層級，低於覆蓋層但高於頁面內容

        // 創建四個覆蓋層，分別覆蓋上、下、左、右邊框
        ['top', 'bottom', 'left', 'right'].forEach(function(side) {
            var overlay = document.createElement('div');
            overlay.id = 'ok_prompt_overlay_' + side;
            overlay.style.position = 'fixed';
            overlay.style.zIndex = '9999';
            overlay.style.backgroundColor = 'transparent';
            overlay.style.cursor = 'pointer';

            if (side === 'top' || side === 'bottom') {
                overlay.style.left = '0';
                overlay.style.width = '100%';
                overlay.style.height = '5px'; // 邊框寬度
                overlay.style[side] = '0';
            } else {
                overlay.style.top = '0';
                overlay.style.height = '100%';
                overlay.style.width = '5px'; // 邊框寬度
                overlay.style[side] = '0';
            }

            // 點擊邊框時設置退出標誌
            overlay.addEventListener('click', function() {
                window.exitInteractionLoop = true;
            });

            document.body.appendChild(overlay);
        });

        // 將邊框容器添加到頁面
        document.body.appendChild(borderContainer);
    })();
    """
    try:
        driver.execute_script(js_script)
    except Exception as e:
        logging.error(f"Failed to inject green border and overlay: {e}")

def userInteraction_to_json_preprocessing(it, interaction, interaction_execution_url, json_recording):
    if interaction['type'] == 'click':
        if 'text' in interaction and interaction['text']:
            clear_record = f"Click on element with text \"{interaction['text']}\""
        else:
            clear_record = f"Click on {interaction['target']} at position ({interaction['x']}, {interaction['y']})"
    
    elif interaction['type'] == 'input':
        clear_record = f"Input \"{interaction['value']}\" into {interaction['target']}"

    elif interaction['type'] == 'scroll':
        clear_record = f"Scroll {interaction['action']} with total_distance: {interaction['total_scroll_distance']}"
    
    elif interaction['type'] == 'navigation':
        clear_record = f"Go back to {interaction['url']}"
    
    else:
        clear_record = "unknown interaction"

    json_recording["userInteraction_recording"].append({
        "Interaction_Step": it,
        "Actual_Interaction": clear_record,
        "Executed_On_URL": interaction_execution_url
    })

def userInteractions_recording(start_web, json_recording, record_dir):
    screenshot_dir = os.path.join(record_dir, "screenshot_recording")
    os.makedirs(screenshot_dir, exist_ok=True)

    # 瀏覽器設定
    options = driver_config()

    # 開啟 Selenium 瀏覽器並前往任務頁面
    driver_task = webdriver.Chrome(options=options)

    # 設定瀏覽器頁面
    driver_task.maximize_window()
    driver_task.get(start_web)

    # 點擊 body 觸發互動
    try:
        driver_task.find_element(By.TAG_NAME, 'body').click()
    except:
        pass
    # 防止按空白鍵自動捲動頁面
    driver_task.execute_script("""window.onkeydown = function(e) {if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea') {e.preventDefault();}};""")

    it = 0
    current_url = None
    it_output = True
    typeinput_buffer = None
    typeinput_buffer_url = None
    finish_recording = False

    # 紀錄起始網站
    logging.info(f'Start from website at {start_web}.')
    json_recording["userInteraction_recording"].append({"Interaction_Step": it, "Actual_Interaction": f"Start from the website at {start_web}.", "Executed_On_URL": "None URL"})
    
    # Iteration 互動迴圈
    while True:
        if finish_recording:
            break

        if it_output:
            it += 1

        # 確保仍然停留在目標視窗
        window_handle_task = driver_task.current_window_handle
        driver_task.switch_to.window(window_handle_task)

        # 確保網頁載入完成
        while True:
            ready_state = driver_task.execute_script("return document.readyState")
            if ready_state == "complete":
                inject_ok_prompt(driver_task)
                break
            else:
                time.sleep(0.5)

        # 擷取螢幕截圖
        img_path = os.path.join(screenshot_dir, 'screenshot_{}.png'.format(it))
        driver_task.save_screenshot(img_path)

        # 注入 JavaScript 監聽用戶行為
        inject_script(driver_task)

        # 跳轉頁面重置
        if current_url == None or driver_task.current_url != current_url:
            scrollY_base = 0
            scrollY_buffer = 0
            scroll_buffer_action = None
            scroll_buffer_url = None
            current_url = driver_task.current_url
        
        # 等待用户交互並記錄
        if it_output:
            logging.info(f'UserInteraction: {it}')
        interactions = []
        while not interactions:
            safe_inject(driver_task)
            interactions = get_user_interactions(driver_task)

            # 檢查是否完成紀錄要退出迴圈
            try:
                exit_loop = driver_task.execute_script("return window.exitInteractionLoop === true;")
                if exit_loop:
                    # 檢查還有沒有buffer要輸出
                    if scroll_buffer_action:
                        scroll_action = {'type': 'scroll', 'action': scroll_buffer_action, 'total_scroll_distance': (scrollY_buffer - scrollY_base)}
                        logging.info(f"User interaction: {scroll_action}")
                        logging.info(f"Interaction is executed on {scroll_buffer_url}")
                        userInteraction_to_json_preprocessing(it=it, interaction=scroll_action, interaction_execution_url=scroll_buffer_url, json_recording=json_recording)
                        scrollY_base = scrollY_buffer
                        scroll_buffer_action = None
                        
                        # for new interaction
                        it += 1
                        logging.info(f'UserInteraction: {it}')
                    # 結束
                    logging.info("########## Finish userInteractions recording ##########")
                    json_recording["userInteraction_recording"].append({"Interaction_Step": it, "Actual_Interaction": f"Task Completed", "Executed_On_URL": current_url})
                    driver_task.quit()
                    finish_recording = True
                    break
            except Exception as e:
                pass

            # 重置檢查項
            it_output = False

            # 未跳轉頁面
            type_interaction_count = 0
            scroll_interaction_count = 0
            for interaction in interactions:
                # 輸入紀錄buffer
                if interaction['type'] == 'input':
                    typeinput_buffer = interaction
                    typeinput_buffer_url = driver_task.current_url
                    type_interaction_count += 1
                
                # 滑動紀錄buffer
                elif interaction['type'] == 'scroll' and (scroll_buffer_action==None or (scroll_buffer_action=='down' and interaction['scrollY']>=scrollY_buffer) or (scroll_buffer_action=='up' and interaction['scrollY']<=scrollY_buffer)):
                    if interaction['scrollY'] > scrollY_base:
                        scroll_buffer_action = 'down'
                    elif interaction['scrollY'] < scrollY_base:
                        scroll_buffer_action = 'up'
                    
                    scrollY_buffer = interaction['scrollY']
                    scroll_buffer_url = driver_task.current_url
                    scroll_interaction_count += 1

                # 滑動方向變換輸出
                elif interaction['type'] == 'scroll' and ((scroll_buffer_action=='down' and interaction['scrollY']<scrollY_buffer) or (scroll_buffer_action=='up' and interaction['scrollY']>scrollY_buffer)):
                    # buffer輸出
                    if typeinput_buffer:
                        logging.info(f"User interaction: {typeinput_buffer}")
                        logging.info(f"Interaction is executed on {typeinput_buffer_url}")
                        userInteraction_to_json_preprocessing(it=it, interaction=typeinput_buffer, interaction_execution_url=typeinput_buffer_url, json_recording=json_recording)
                        typeinput_buffer = None
                        
                        # for new interaction
                        it += 1
                        logging.info(f'UserInteraction: {it}')
                    
                    scroll_action = {'type': 'scroll', 'action': scroll_buffer_action, 'total_scroll_distance': (scrollY_buffer - scrollY_base)}
                    logging.info(f"User interaction: {scroll_action}")
                    logging.info(f"Interaction is executed on {scroll_buffer_url}")
                    userInteraction_to_json_preprocessing(it=it, interaction=scroll_action, interaction_execution_url=scroll_buffer_url, json_recording=json_recording)

                    scrollY_base = scrollY_buffer
                    scroll_buffer_action = None
                    it_output = True

                # 其他輸出
                else:
                    if interaction['type'] in ['click', 'navigation']:
                        # buffer輸出
                        if typeinput_buffer:
                            logging.info(f"User interaction: {typeinput_buffer}")
                            logging.info(f"Interaction is executed on {typeinput_buffer_url}")
                            userInteraction_to_json_preprocessing(it=it, interaction=typeinput_buffer, interaction_execution_url=typeinput_buffer_url, json_recording=json_recording)
                            typeinput_buffer = None
                            
                            # for new interaction
                            it += 1
                            logging.info(f'UserInteraction: {it}')
                        
                        elif scroll_buffer_action:
                            scroll_action = {'type': 'scroll', 'action': scroll_buffer_action, 'total_scroll_distance': (scrollY_buffer - scrollY_base)}
                            logging.info(f"User interaction: {scroll_action}")
                            logging.info(f"Interaction is executed on {scroll_buffer_url}")
                            userInteraction_to_json_preprocessing(it=it, interaction=scroll_action, interaction_execution_url=scroll_buffer_url, json_recording=json_recording)
                            scrollY_base = scrollY_buffer
                            scroll_buffer_action = None
                            
                            # for new interaction
                            it += 1
                            logging.info(f'UserInteraction: {it}')
                    
                    logging.info(f"User interaction: {interaction}")
                    logging.info(f"Interaction is executed on {current_url}")
                    userInteraction_to_json_preprocessing(it=it, interaction=interaction, interaction_execution_url=current_url, json_recording=json_recording)
                    it_output = True
            
            # 清空userInteractions
            if len(interactions) != 0:
                clear_userInteractions(driver_task)
            
            # 打字或滑動buffer處理
            if (not it_output) and ((type_interaction_count != 0 and type_interaction_count == len(interactions)) or (scroll_interaction_count != 0 and scroll_interaction_count == len(interactions))):
                img_path = os.path.join(screenshot_dir, 'screenshot_{}.png'.format(it+1))
                driver_task.save_screenshot(img_path)
                interactions = []
            
            # 跳轉頁面
            if driver_task.current_url != current_url and not it_output:
                # logging.info(f"SPECIAL: {it}, {driver_task.current_url}")
                driver_task.execute_script("localStorage.setItem('pendingPopstateInteraction', 'null');")
                safe_inject(driver_task)
                interactions = get_user_interactions(driver_task)
                if interactions:
                    for interaction in interactions:
                        if interaction['type'] in ['click', 'navigation']:
                            # buffer輸出
                            if typeinput_buffer:
                                logging.info(f"User interaction: {typeinput_buffer}")
                                logging.info(f"Interaction is executed on {typeinput_buffer_url}")
                                userInteraction_to_json_preprocessing(it=it, interaction=typeinput_buffer, interaction_execution_url=typeinput_buffer_url, json_recording=json_recording)
                                typeinput_buffer = None
                                
                                # for new interaction
                                it += 1
                                logging.info(f'UserInteraction: {it}')
                            
                            elif scroll_buffer_action:
                                scroll_action = {'type': 'scroll', 'action': scroll_buffer_action, 'total_scroll_distance': (scrollY_buffer - scrollY_base)}
                                logging.info(f"User interaction: {scroll_action}")
                                logging.info(f"Interaction is executed on {scroll_buffer_url}")
                                userInteraction_to_json_preprocessing(it=it, interaction=scroll_action, interaction_execution_url=scroll_buffer_url, json_recording=json_recording)
                                scrollY_base = scrollY_buffer
                                scroll_buffer_action = None
                                
                                # for new interaction
                                it += 1
                                logging.info(f'UserInteraction: {it}')
                            
                            logging.info(f"User interaction: {interaction}")
                            logging.info(f"Interaction is executed on {current_url}")
                            userInteraction_to_json_preprocessing(it=it, interaction=interaction, interaction_execution_url=current_url, json_recording=json_recording)
                            it_output = True
                    # 清空userInteractions
                    clear_userInteractions(driver_task)
                break

    # 最終記錄到json中
    with open(os.path.join(record_dir, "userInteractions_recording.json"), 'w', encoding='utf-8') as record_file:
        json.dump(json_recording, record_file, indent=4, ensure_ascii=False)
# --------------------------------------------------------------------

# Agent推斷操作背後的邏輯或原因 ----------------------------------------
def format_msg(it, init_msg, pdf_obs, warn_obs, web_img_b64, web_text):
    if it == 1:
        init_msg += f"I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"
        init_msg_format = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': init_msg},
            ]
        }
        init_msg_format['content'].append({"type": "image_url",
                                           "image_url": {"url": f"data:image/png;base64,{web_img_b64}"}})
        return init_msg_format
    else:
        if not pdf_obs:
            curr_msg = {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': f"Observation:{warn_obs} please analyze the attached screenshot and give the Thought and Action. I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"},
                    {
                        'type': 'image_url',
                        'image_url': {"url": f"data:image/png;base64,{web_img_b64}"}
                    }
                ]
            }
        else:
            curr_msg = {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': f"Observation: {pdf_obs} Please analyze the response given by Assistant, then consider whether to continue iterating or not. The screenshot of the current page is also attached, give the Thought and Action. I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"},
                    {
                        'type': 'image_url',
                        'image_url': {"url": f"data:image/png;base64,{web_img_b64}"}
                    }
                ]
            }
        return curr_msg

def call_gemini_api(parameter, gemini_client, messages, img):
    retry_times = 0
    while retry_times < 10:
        try:
            logging.info('Calling Gemini API...')

            # 設定請求內容
            # 正確格式化 `messages`
            contents = [{"role": "user", "parts": [{"text": m["content"] if isinstance(m["content"], str) else m["content"][0]["text"]}]} for m in messages]

            # 如果有圖片，加上圖片訊息
            if img:
                contents.append({"role": "user", "parts": [{"inline_data": {"mime_type": "image/png", "data": img}}]})

            # 呼叫 API
            gemini_response = gemini_client.generate_content(
                contents=contents,
                generation_config=GenerationConfig(
                    max_output_tokens=1000,
                    temperature=parameter["temperature"]
                )
            )
            return False, gemini_response.text

        except Exception as e:
            logging.info(f'Error occurred, retrying. Error type: {type(e).__name__}')
        
            if type(e).__name__ == 'RateLimitError':
                time.sleep(10)

            elif type(e).__name__ == 'APIError':
                time.sleep(15)

            elif type(e).__name__ == 'InvalidRequestError':
                return True, None

            else:
                return True, None

        retry_times += 1
        if retry_times == 10:
            logging.info('Retrying too many times')
            return True, None

def ActionReasoning_Agent_thinking(record_dir, parameter):
    logging.info(f'########## ARA start Action Reasoning ##########')

    # 建立 API 客戶端
    gemini.configure(api_key=parameter["api_key"])
    client = gemini.GenerativeModel(parameter["api_model"])

    # 讀取 user interaction 紀錄
    recording_path = os.path.join(record_dir, "userInteractions_recording.json")
    with open(recording_path, 'r', encoding='utf-8') as f:
        json_recording = json.load(f)
    steps = json_recording['userInteraction_recording']

    # 找到截圖資料夾
    screenshot_dir = os.path.join(record_dir, "screenshot_recording")

    # 建立輸出資料夾
    reasoning_dir = os.path.join(record_dir, "action_reasoning")
    os.makedirs(reasoning_dir, exist_ok=True)

    # 開始逐步處理
    for i in range(len(steps) - 1):  # 最後一步是 Task Completed，不需要推理
        step_info = steps[i]

        step_text = step_info['Actual_Interaction']
        current_img_path = os.path.join(screenshot_dir, f"screenshot_{i}.png")
        next_img_path = os.path.join(screenshot_dir, f"screenshot_{i+1}.png")

        # 讀取圖片並編碼成base64
        import base64
        def encode_image_to_base64(img_path):
            with open(img_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')

        img_b64_current = encode_image_to_base64(current_img_path)
        img_b64_next = encode_image_to_base64(next_img_path)

        # 準備 prompt
        user_prompt = (
            f"The task is: \"{json_recording['task_question']}\".\n"
            f"Now observe the current operation step:\n"
            f"\"{step_text}\"\n\n"
            f"You are given two screenshots:\n"
            f"1. Screenshot **before** this action.\n"
            f"2. Screenshot **after** this action.\n\n"
            f"Please carefully analyze both screenshots and the action description, and infer the **reasoning and intention behind this action**.\n"
            f"Explain in detail why the user might have performed this action given the task goal.\n"
            f"Return only the reasoning without repeating the action description."
        )

        # 包裝成 messages 格式 (Gemini格式)
        messages = [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': user_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64_current}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64_next}"}},
            ]
        }]

        # 呼叫 Gemini API
        error, response_text = call_gemini_api(parameter, client, messages, img=None)

        if error:
            logging.error(f"Failed to reason step {i}")
            continue

        # 儲存結果
        reasoning_output_path = os.path.join(reasoning_dir, f"reasoning_step_{i}.txt")
        with open(reasoning_output_path, 'w', encoding='utf-8') as out_file:
            out_file.write(response_text)

        logging.info(f"Finished reasoning step {i}")
# --------------------------------------------------------------------

def main(ARA_parameter, task_ques="Find Kevin Duran'ts bio", start_web="https://www.google.com/"):
    # 任務初始化
    task_dir = os.path.join('userInteraction_recording', 'recording_{}'.format(len(os.listdir('userInteraction_recording'))))
    os.makedirs(task_dir, exist_ok=True)
    setup_logger(task_dir)
    logging.info(f'########## {task_ques} ##########')
    json_recording = {"task_question": task_ques, "userInteraction_recording": []}

    # 記錄使用者操作
    userInteractions_recording(start_web=start_web, json_recording=json_recording, record_dir=task_dir)

    # Agent推斷操作邏輯
    # ActionReasoning_Agent_thinking(record_dir=task_dir, parameter=ARA_parameter)

if __name__ == '__main__':
    with open("ARA_parameter.json", 'r') as parameterfile:
        ARA_parameter = json.load(parameterfile)
    os.makedirs('userInteraction_recording', exist_ok=True)
    main(ARA_parameter)
    print('End of process')
