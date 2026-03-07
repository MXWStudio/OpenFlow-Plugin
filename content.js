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
    
    // === 去除修饰词，只保留真正游戏名 ===
    // 加上您需要去除的词语
    const removeWords = ['华为', 'vivo', '荣耀', 'OPPO', '小米', '赛诺斯', '华为指天椒', '指天椒'];
    
    // 全局且忽略大小写替换
    removeWords.forEach(word => {
        projectNameStr = projectNameStr.replace(new RegExp(word, 'ig'), '');
    });
    
    // 去除4位日期的数字串 (例如：0304)
    projectNameStr = projectNameStr.replace(/\d{4}/g, '');
    
    // 清理首尾和连续的多重短横线
    projectNameStr = projectNameStr.replace(/-+/g, '-').replace(/^-|-$/g, '').trim();

    // 保底：如果在过度提取后变成了空字符串，就恢复原样
    if (!projectNameStr) {
        projectNameStr = rawTaskName;
    }

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

// 接收来自 popup.js 的消息并执行提取
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "EXTRACT_DOM") {
    const result = extractDataFromPage();
    sendResponse(result);
  }
});
