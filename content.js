// content.js
function extractDataFromPage() {
  try {
    // 1. 提取基础信息 (利用 querySelector 匹配网页中的具体结构)
    // 根据 PRD 中的 HTML 结构，寻找包含文本的 span 或 div
    // 这里的选择器需要根据目标网站真实的 DOM 结构微调
    const rawText = document.body.innerText;
    
    // 动态提取项目名称
    // 动态提取项目名称（从左侧选中的列表项提取）
    let rawTaskName = "";
    
    // 1. 找到所有可能是任务名称的文本节点（例如：赛诺斯-小火车呜呜呜-华为-0304）
    const candidates = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let textNode;
    while ((textNode = walker.nextNode())) {
        const text = textNode.nodeValue.trim();
        // 匹配含有短横线、没有换行且长度适中的字符串
        if (text.includes('-') && !text.includes('\n') && text.length > 5 && text.length < 80) {
            candidates.push({ node: textNode.parentElement, text: text });
        }
    }

    // 2. 遍历这些候选节点，检查它的容器（向上找几层）是否有被选中的样式（背景色发灰，或包含 active/selected 类名）
    for (const item of candidates) {
        let el = item.node;
        let isSelected = false;
        for (let i = 0; i < 5 && el && el !== document.body; i++) {
            const className = (typeof el.className === 'string' ? el.className : '').toLowerCase();
            const bgColor = window.getComputedStyle(el).backgroundColor;
            
            // 依据类名判断选中状态
            if (className.includes('active') || className.includes('select') || className.includes('current')) {
                isSelected = true;
                break;
            }
            // 依据背景颜色判断（非透明且非白色），并且宽度适中（如左侧列表项）
            if (bgColor && bgColor !== 'rgba(0, 0, 0, 0)' && bgColor !== 'transparent' && bgColor !== 'rgb(255, 255, 255)') {
                if (el.offsetWidth > 50 && el.offsetWidth < 600) {
                    isSelected = true;
                    break;
                }
            }
            el = el.parentElement;
        }
        if (isSelected) {
            rawTaskName = item.text;
            break;
        }
    }

    // 如果依然没找到选中的列表项提取出名字，退阶使用基础正则
    if (!rawTaskName) {
        const nameMatch = rawText.match(/(?:项目名称|任务名称|项目游戏名称|产品名称)[：:\s]*([a-zA-Z0-9\u4e00-\u9fa5\-\_:]+)/);
        if (nameMatch && nameMatch[1]) {
            rawTaskName = nameMatch[1].trim();
        } else {
            const fallbackMatch = rawText.match(/[\u4e00-\u9fa5A-Za-z0-9]+(?:-[\u4e00-\u9fa5A-Za-z0-9]+){1,}/);
            if (fallbackMatch) {
                rawTaskName = fallbackMatch[0].trim();
            }
        }
    }

    // 此时 rawTaskName 为类似 "赛诺斯-小火车呜呜呜-华为-0304"
    let projectNameStr = rawTaskName || "未知项目";
    
    // 将项目全名传给后续处理流程，不要破坏原始的 "-" 分割结构，
    // 以便 popup.js 能够进行更精准的最长匹配提取。
    projectNameStr = rawTaskName;

    // 匹配网页文本中的“素材类型：视频”或“平面”
    let materialType = '未知';
    const typeMatch = rawText.match(/素材类型[：:]\s*(视频|平面)/);
    if (typeMatch) {
        materialType = typeMatch[1];
    } else {
        materialType = rawText.includes('视频') ? '视频' : '平面';
    }
    
    // 提取原创套数（如果页面中有 "原创: 5套" 等相关字眼），默认给 0 或者留空让业务自己算也可以
    let originalCount = 0;
    const originalMatch = rawText.match(/原创.*?(\d+)\s*套/);
    if (originalMatch) {
       originalCount = parseInt(originalMatch[1], 10);
    } else {
       // 未找到明确的“原创: X套”，根据要求有的版位可能单图出几个延展
       // 这是一个保底提取。
    }

    // 2. 提取尺寸列表 (寻找对应的卡片容器)
    const sizeCards = document.querySelectorAll('section.bg-white.p-4.shadow-md');
    let sizeDetails = [];
    
    sizeCards.forEach(card => {
       const typeName = card.querySelector('.font-bold')?.innerText || '未知版位';
       const items = card.querySelectorAll('.mt-2.p-2'); // 获取每一行尺寸
       
       items.forEach(item => {
           const spans = item.querySelectorAll('span.flex.items-center.justify-center');
           if(spans.length >= 3) {
               sizeDetails.push({
                   "版位类型": typeName,
                   "分辨率": spans[0].innerText.trim(),
                   "大小限制": spans[1].innerText.trim(),
                   "所需数量": spans[2].innerText.replace('所需数量：', '').trim()
               });
           }
       });
    });

    // 提取更多附加信息 (扩展 JSON 返回内容，把能提取的尽可能都拿出来)
    const extraData = {};
    const lines = rawText.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    const keywordsToLookAhead = [
        "任务ID", "需求方", "制作人", "集团名称", "投放媒体", "应用类型", 
        "素材用途", "业务分组", "业务承接", "期望完成日期", "预计交付时间", "投放预算",
        "下单人", "下单时间", "优先级", "需求详情", "注意事项", "安装包链接", 
        "素材参考链接", "参考图片", "参考视频", "参考文件", "已制素材", 
        "下单方式", "素材数"
    ];

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];
        
        // 过滤掉纯符号或太短/太长的线
        if (/^[^\w\u4e00-\u9fa5]+$/.test(line) || line.length > 300) continue;

        // 1. 匹配单行内的 "键：值" 或 "键: 值"
        const inlineMatch = line.match(/^([a-zA-Z\u4e00-\u9fa5]{2,10})\s*[：:]\s*(.+)$/);
        if (inlineMatch) {
            let key = inlineMatch[1].trim();
            let val = inlineMatch[2].trim();
            // 不覆盖已有且看起来有意义的值
            if (val && val !== "/" && val !== "无" && !extraData[key]) {
                 extraData[key] = val;
            }
        } else {
            // 2. 匹配上下行的 "键\n值"
            const cleanLine = line.replace(/[：:]$/, '').trim();
            if (keywordsToLookAhead.includes(cleanLine) && i + 1 < lines.length) {
                const nextLine = lines[i + 1];
                // 如果下一行不是关键字且不是常见按钮文字，作为它的值
                if (!keywordsToLookAhead.includes(nextLine.replace(/[：:]$/, '').trim()) 
                    && nextLine !== "复制" && nextLine !== "查看" && nextLine.length < 500) {
                     if (!extraData[cleanLine] || extraData[cleanLine] === "/" || extraData[cleanLine] === "无") {
                         extraData[cleanLine] = nextLine;
                     }
                }
            }
        }
    }

    // 3. 组装返回数据，将额外数据平铺在最后
    return {
      success: true,
      data: {
        "项目游戏名称": projectNameStr,
        "素材类型": materialType,
        "原创套数": originalCount,
        "尺寸要求明细": sizeDetails,
        ...extraData
      }
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * 辅助函数：等待指定的毫秒数 (sleep)
 * @param {number} ms 毫秒数
 * @returns {Promise<void>}
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * 自动遍历点击并抓取数据的异步核心逻辑
 * @param {Function} sendResponse 用于向后台或 popup 返回通信结果的回调函数
 */
async function extractBulkDataFromPageAsync(sendResponse) {
  try {
    const extractedDataList = [];
    
    // 1. 查找左侧列表：获取所有带有 class="ant-tag-yellow" 并确保文本是“未开始”的元素
    const tagElements = Array.from(document.querySelectorAll('.ant-tag.ant-tag-yellow'));
    const unstartedTags = tagElements.filter(tag => tag.innerText.trim() === '未开始');
    
    // 如果找不到未开始的任务，直接返回空数组
    if (unstartedTags.length === 0) {
      console.log('[SmartAd 助手] 未找到状态为“未开始”的任务');
      sendResponse({ success: true, data: [] });
      return;
    }

    console.log(`[SmartAd 助手] 共找到 ${unstartedTags.length} 个未开始的任务，准备开始遍历...`);

    // 2. 循环遍历未开始的任务标签
    for (let i = 0; i < unstartedTags.length; i++) {
        const tag = unstartedTags[i];
        
        // 3. 提取左侧基础信息：向上查找到任务卡片容器
        const cardContainer = tag.closest('.p-4.cursor-pointer');
        if (!cardContainer) {
            console.warn(`[SmartAd 助手] 第 ${i + 1} 个标签未找到父级卡片容器，已跳过`);
            continue;
        }

        // 提取卡片的全部文本内容（用于后续正则匹配）
        const cardText = cardContainer.innerText;

        // 提取项目名称
        const projectNameEl = cardContainer.querySelector('.truncate');
        const projectName = projectNameEl ? projectNameEl.innerText.trim() : '未知项目';

        // 提取素材类型 (包含视频或平面)
        let materialType = '未知类型';
        if (cardText.includes('视频')) {
            materialType = '视频';
        } else if (cardText.includes('平面')) {
            materialType = '平面';
        }

        // 提取所需套数 (正则匹配 "所需X套")
        let requiredSets = 0;
        const setsMatch = cardText.match(/所需(\d+)套/);
        if (setsMatch && setsMatch[1]) {
            requiredSets = parseInt(setsMatch[1], 10);
        }

        // 4. 模拟点击与等待
        console.log(`[SmartAd 助手] 正在点击并采集任务: 【${projectName}】...`);
        cardContainer.click();
        
        // 动态等待机制：React / Vue 单页应用点击后会有明显的网络请求和转圈动画
        // 1. 先等待初始网络请求发出的动画出现 (最多 500ms)
        let spinnerAppeared = false;
        for (let t = 0; t < 5; t++) {
            await sleep(100);
            if (document.querySelector('.ant-spin-spinning, .ant-spin-blur')) {
                spinnerAppeared = true;
                break;
            }
        }
        
        // 2. 等待动画彻底消失 (最多再等 5000ms)，如果没出现过就算了直接兜底等
        if (spinnerAppeared) {
            for (let t = 0; t < 50; t++) {
                await sleep(100);
                if (!document.querySelector('.ant-spin-spinning, .ant-spin-blur')) {
                    break;
                }
            }
        }
        
        // 3. 稳妥起见，统一再强等 1000ms 以确保文字全部渲染进纯净的 DOM 树
        await sleep(1000);
        
        // 5. 提取右侧详情和全量附加字典
        const rightPanel = document.querySelector('.ant-tabs-content-holder') || document.body;
        const detailItems = [];
        
        // 5.1 获取尺寸要求
        const sizeCards = document.querySelectorAll('section.bg-white.p-4.shadow-md');
        if (sizeCards.length > 0) {
            sizeCards.forEach(card => {
                const typeName = card.querySelector('.font-bold')?.textContent.trim() || '未知版位';
                const items = card.querySelectorAll('.mt-2.p-2'); 
                
                items.forEach(item => {
                    const spans = item.querySelectorAll('span.flex.items-center.justify-center');
                    if (spans.length >= 3) {
                        detailItems.push({
                            resolution: spans[0].textContent.trim(),
                            sizeLimit: spans[1].textContent.trim(),
                            requiredQuantity: spans[2].textContent.replace(/[^\d]/g, '').trim(),
                            positionType: typeName 
                        });
                    }
                });
            });
        }
        
        // fallback to old logic if no cards found
        if (detailItems.length === 0) {
            const inputs = Array.from(rightPanel.querySelectorAll('input.ant-input'));
            const resolutionRegex = /\d+\s*[*xX]\s*\d+/;
            const resolutionInputs = inputs.filter(input => resolutionRegex.test(input.value));

            resolutionInputs.forEach(resInput => {
                const resolution = resInput.value.trim();
                let sizeLimit = '', requiredQuantity = '';
                const rowWrapper = resInput.closest('.ant-row') || resInput.parentElement.parentElement;
                if (rowWrapper) {
                    const rowInputs = Array.from(rowWrapper.querySelectorAll('input.ant-input'));
                    const currentIndex = rowInputs.indexOf(resInput);
                    if (currentIndex !== -1) {
                        if (rowInputs[currentIndex + 1]) sizeLimit = rowInputs[currentIndex + 1].value.trim();
                        if (rowInputs[currentIndex + 2]) requiredQuantity = rowInputs[currentIndex + 2].value.trim();
                    }
                }
                detailItems.push({ resolution, sizeLimit, requiredQuantity });
            });
        }

        // 5.2 大面积从文本中提取各种“键值对”(例如: 制作人/应用类型/期望完成日期)
        const extraData = {};
        const lines = rightPanel.innerText.split('\n').map(l => l.trim()).filter(Boolean);
        
        // 所有期望支持的字段集合
        const knownKeys = [
            '制作人', '制作者', '公司名称', '公司主体', '集团名称', '设计小组', '业务分组', '需求归属', 
            '需求属性', '投放媒体', '渠道', '应用类型', '素材用途', '工具标签', '安装包链接', 
            '参考文件', '参考图片', '参考视频', '已制素材', '业务承接', '优先级', '注意事项',
            '需求详情', '期望完成日期', '预计交付时间', '截止日期', '任务ID', '投放预算',
            '投放日预算', '下单方式', '下单人', '下单时间', '素材数', '素材类型'
        ];

        for (let j = 0; j < lines.length; j++) {
            let line = lines[j];
            // 过滤无用乱码行
            if (/^[^\w\u4e00-\u9fa5]+$/.test(line) || line.length > 500) continue;

            // 情境A：同在一行，如 "业务承接: AI创意素材组" 或 "业务承接： AI创意素材组"
            const inlineMatch = line.match(/^([a-zA-Z\u4e00-\u9fa5]{2,10})\s*[：:]\s*(.+)$/);
            if (inlineMatch) {
                let key = inlineMatch[1].trim();
                let val = inlineMatch[2].trim();
                if (!extraData[key] && val && val !== '无' && val !== '/') {
                    extraData[key] = val;
                }
            } else {
                // 情境B：空格分割，如 "下单时间 2026-03-04"
                const spaceMatch = line.match(/^([a-zA-Z\u4e00-\u9fa5]{2,10})\s+(.+)$/);
                if(spaceMatch && knownKeys.includes(spaceMatch[1].trim())) {
                    let key = spaceMatch[1].trim();
                    let val = spaceMatch[2].trim();
                    if (!extraData[key] && val && val !== '无' && val !== '/') {
                        extraData[key] = val;
                    }
                } else {
                    // 情境C：换行分布，本行为键，下一行为值
                    const cleanLine = line.replace(/[：:]$/, '').trim();
                    if (knownKeys.includes(cleanLine) && j + 1 < lines.length) {
                        const nextLine = lines[j + 1];
                        if (
                            !knownKeys.includes(nextLine.replace(/[：:]$/, '').trim()) && 
                            nextLine !== "复制" && nextLine !== "查看" && nextLine !== "/" &&
                            nextLine.length < 500
                        ) {
                            if (!extraData[cleanLine]) {
                                extraData[cleanLine] = nextLine;
                            }
                        }
                    }
                }
            }
        }

        // 6. 组装数据并推入数组
        // 如果右侧详情有明确的素材类型，则以右侧详情为准
        if (extraData['素材类型'] && (extraData['素材类型'].includes('平面') || extraData['素材类型'].includes('视频'))) {
            materialType = extraData['素材类型'].includes('视频') ? '视频' : '平面';
        }

        extractedDataList.push({
            projectName,
            materialType,
            requiredSets,
            details: detailItems,
            ...extraData // 将额外提取的所有附加字段全量展开合并到该条记录的顶层
        });
    }

    console.log('[SmartAd 助手] 批量提取完成！', extractedDataList);
    // 所有循环结束后，返回最终数据
    sendResponse({ success: true, data: extractedDataList });

  } catch (error) {
    console.error('[SmartAd 助手] 抓取过程中发生异常:', error);
    sendResponse({ success: false, error: error.message });
  }
}

// 接收来自 popup.js 的消息并执行提取
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "EXTRACT_DOM") {
    // 原始单次抓取逻辑
    const result = extractDataFromPage();
    sendResponse(result);
  } else if (request.action === "EXTRACT_BULK_DOM") {
    // 新增批量抓取逻辑
    extractBulkDataFromPageAsync(sendResponse);
    // 必须隐式 return true 告诉 Chrome 使用异步的 sendResponse
    return true;
  }
});
