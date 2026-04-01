// popup.js
let extractedBulkData = [];
const EXTRACTED_BULK_DATA_STORAGE_KEY = 'extractedBulkData';

function getStoredExtractedBulkData() {
    return new Promise((resolve, reject) => {
        chrome.storage.local.get(EXTRACTED_BULK_DATA_STORAGE_KEY, (result) => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
                return;
            }

            resolve(result[EXTRACTED_BULK_DATA_STORAGE_KEY]);
        });
    });
}

function saveExtractedBulkData(dataList) {
    return new Promise((resolve, reject) => {
        chrome.storage.local.set({ [EXTRACTED_BULK_DATA_STORAGE_KEY]: dataList }, () => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
                return;
            }

            resolve();
        });
    });
}

function escapeHtmlText(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function setExtractButtonPrimaryState() {
    const btn = document.getElementById('extractBtn');
    btn.disabled = false;
    btn.className = 'btn btn-primary';
    btn.innerHTML = '<span>📥</span> 提取当前页面任务';
}

function setExtractButtonSecondaryState() {
    const btn = document.getElementById('extractBtn');
    btn.disabled = false;
    btn.className = 'btn btn-secondary';
    btn.innerHTML = '<span>🔄</span> 重新提取任务';
}

function setExtractButtonLoadingState() {
    const btn = document.getElementById('extractBtn');
    btn.disabled = true;
    btn.className = 'btn btn-primary';
    btn.innerHTML = '<span>⏳</span> 提取中...';
}

function hidePreviewSections() {
    document.getElementById('statusArea').style.display = 'none';
    document.getElementById('listWrapper').style.display = 'none';
    document.getElementById('exportActions').style.display = 'none';
}

async function restoreExtractedBulkData() {
    try {
        const cachedData = await getStoredExtractedBulkData();
        if (Array.isArray(cachedData) && cachedData.length > 0) {
            extractedBulkData = cachedData;
            renderPreview(extractedBulkData);
        }
    } catch (err) {
        console.error('恢复提取缓存失败:', err);
    }
}

setExtractButtonPrimaryState();
hidePreviewSections();
void restoreExtractedBulkData();

document.getElementById('extractBtn').addEventListener('click', async () => {
    // 1. 按钮防抖与提示交互
    setExtractButtonLoadingState();

    try {
        // 获取当前活动标签页
        let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // 注入 content.js (如果尚未注入)
        await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content.js']
        });

        // 2. 发送批量抓取指令
        // 给一点点延迟确保 content.js 加载完毕
        setTimeout(() => {
            chrome.tabs.sendMessage(tab.id, { action: "EXTRACT_BULK_DOM" }, async (response) => {
                // 恢复按钮状态
                setExtractButtonPrimaryState();

                if (chrome.runtime.lastError) {
                    alert("无法连接到页面脚本，请刷新页面后重试。\n错误信息: " + chrome.runtime.lastError.message);
                    return;
                }

                if (response && response.success) {
                    extractedBulkData = Array.isArray(response.data) ? response.data : [];

                    try {
                        await saveExtractedBulkData(extractedBulkData);
                    } catch (err) {
                        console.error('保存提取缓存失败:', err);
                        alert("保存提取数据失败：" + err.message);
                    }
                    if (extractedBulkData.length === 0) {
                        hidePreviewSections();
                        alert("未找到任何状态为“未开始”的任务！");
                    } else {
                        renderPreview(extractedBulkData);
                    }
                } else {
                    alert("提取失败！\n" + (response?.error || '未知错误'));
                }
            });
        }, 150);
        
    } catch (err) {
        setExtractButtonPrimaryState();
        alert("执行脚本发生错误：" + err.message);
    }
});

/**
 * 渲染预览界面
 */
function renderPreview(dataList) {
    let graphicCount = 0;
    let videoCount = 0;
    let wdzCount = 0; // 温典战数量统计

    dataList.forEach(task => {
        const materialType = task.materialType || task["素材类型"] || "";
        if (materialType.includes("平面")) {
            graphicCount += 1;
        }
        if (materialType.includes("视频")) {
            videoCount += 1;
        }

        const orderer = task["下单人"] || "";
        if (orderer.includes("温典战")) {
            wdzCount += 1;
        }
    });

    let statusHtml =
        '<span class="badge badge-success">✅ 共 ' + dataList.length + ' 个</span>' +
        '<span class="badge badge-blue">平面: ' + graphicCount + '</span>' +
        '<span class="badge badge-purple">视频: ' + videoCount + '</span>';

    if (wdzCount > 0) {
        statusHtml += '<div class="badge badge-red">特殊需求-AI批量制作-温典战 (' + wdzCount + '个)</div>';
    }

    document.getElementById('statusArea').innerHTML = statusHtml;
    document.getElementById('statusArea').style.display = 'flex';
    document.getElementById('listWrapper').style.display = 'block';
    document.getElementById('exportActions').style.display = 'flex';
    setExtractButtonSecondaryState();

    const ul = document.getElementById('taskList');
    ul.innerHTML = '';
    
    dataList.forEach(task => {
        const projectName = task.projectName || task["项目名称"] || '未知项目';
        const detailsCount = task.details ? task.details.length : 0;
        const requiredSets = task.requiredSets || task["所需套数"] || task["素材数"] || '';
        const metaParts = [`${detailsCount} 个尺寸`];
        const safeProjectName = escapeHtmlText(projectName);
        const orderer = task["下单人"] || "";

        if (requiredSets) {
            metaParts.push(`数量 ${requiredSets}`);
        }
        
        let taskNameHtml = safeProjectName;
        if (orderer.includes("温典战")) {
            taskNameHtml += '<span class="badge-small-red">温典战</span>';
        }

        let li = document.createElement('li');
        li.className = 'task-item';
        li.innerHTML =
            '<span class="task-name" title="' + safeProjectName + '">' + taskNameHtml + '</span>' +
            '<span class="task-meta">' + escapeHtmlText(metaParts.join(' · ')) + '</span>';
        ul.appendChild(li);
    });
}

/**
 * 展平嵌套的 JSON 数据以便于导出 Excel
 * 结构：任务(1) -> 尺寸要求明细(N) ===展平===> N 行数据
 */
function flattenDataForExport(dataList) {
    const flatArray = [];
    
    dataList.forEach(task => {
        const baseInfo = {
            "项目游戏名称": task.projectName,
            "素材类型": task.materialType,
            "所需套数": task.requiredSets,
            "状态": "未开始"
        };
        
        // 如果该任务有具体尺寸，则针对每个尺寸生成一条记录
        if (task.details && task.details.length > 0) {
            task.details.forEach(detail => {
                flatArray.push({
                    ...baseInfo,
                    "版位类型": detail.positionType || "-",
                    "分辨率": detail.resolution,
                    "大小限制": detail.sizeLimit,
                    "尺寸所需数量": detail.requiredQuantity
                });
            });
        } else {
            // 如果该任务根本没有任何尺寸要求，也保底输出一条记录
            flatArray.push({
                ...baseInfo,
                "版位类型": "-",
                "分辨率": "-",
                "大小限制": "-",
                "尺寸所需数量": "-"
            });
        }
    });

    return flatArray;
}

// 3. 导出 JSON 功能
document.getElementById('exportJsonBtn').addEventListener('click', () => {
    if (!extractedBulkData || extractedBulkData.length === 0) {
        alert("没有可导出的数据！");
        return;
    }
    
    // 助手函数：拆分项目名称，提取游戏名，灵活过滤冗余信息
    const splitProjectName = (fullName, company, channel) => {
        if (!fullName) return { gameName: "未知项目", fullName: "未知项目" };
        const parts = fullName.split('-');
        if (parts.length <= 1) return { gameName: fullName, fullName: fullName };
        if (parts.length === 2) return { gameName: parts[1].trim(), fullName: fullName };

        const knownChannels = ["华为", "穿山甲", "广点通", "快手", "腾讯", "抖音", "头条", "oppo", "vivo", "小米", "百度", "b站", "微信", "朋友圈", "优量汇", "巨量", "巨量引擎", "苹果", "ios", "安卓", "android"];
        const commonTags = ["手动", "自动", "竖版", "横版", "测试", "常规", "首发", "图文", "视频", "平面", "自投", "代投"];

        let candidates = parts.slice(1).filter(p => {
            const pt = p.trim().toLowerCase();
            if (channel && pt === channel.toLowerCase()) return false;
            if (company && pt === company.toLowerCase()) return false;
            if (company && pt.includes(company.toLowerCase())) return false;
            if (knownChannels.includes(pt)) return false;
            if (commonTags.includes(pt)) return false;
            if (/^\d{4}$/.test(pt) || /^\d{6}$/.test(pt) || /^\d{8}$/.test(pt)) return false;
            return true;
        });

        if (candidates.length > 0) {
            // 返回最长的那一段作为游戏名
            candidates.sort((a, b) => b.trim().length - a.trim().length);
            return { gameName: candidates[0].trim(), fullName: fullName };
        }
        
        return { gameName: parts[1].trim(), fullName: fullName };
    };

    // 按目标结构重建 JSON 列表
    const formattedDataList = extractedBulkData.map(task => {
        const orderedData = {};

        // 公司名称和集团需要提前获取用于项目名清洗
        const companyName = task["集团名称"] || task["公司名称"] || task["公司主体"] || "赛诺斯";
        const mediaChannel = task["投放媒体"] || task["渠道"] || "华为";

        const { gameName, fullName } = splitProjectName(task.projectName || task["项目名称"], companyName, mediaChannel);
        
        // 日期处理
        const today = new Date();
        const dateStr = today.toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\//g, '/');
        
        // 核心值
        const materialTypeRaw = task.materialType || task["素材类型"] || "";
        const isGraphic = materialTypeRaw.includes("平面");

        // 统计套数 (素材数)
        let rawMaterialCount = 4;
        const rawSets = task["所需套数"] || task["素材数"];
        if (rawSets) {
            const match = String(rawSets).match(/\d+/);
            if (match) rawMaterialCount = parseInt(match[0], 10);
        }

        const details = task.details || [];
        const makerName = task["制作人"] || task["制作者"] || "孟祥伟";

        // 组装头部字段
        if (isGraphic) {
            // 平面模板 (14个字段)
            orderedData["日期"] = dateStr;
            orderedData["制作人"] = makerName;
            orderedData["项目名称"] = gameName;
            orderedData["公司名称"] = companyName;
            orderedData["集团"] = companyName;
            orderedData["需求方"] = task["需求方"] || "移动终端事业部";
            orderedData["网易标识"] = "非网易";
            orderedData["业务分类"] = task["需求归属"] || task["业务分组"] || "移动终端-IAA";
            orderedData["广告策略"] = "竞价";
            orderedData["素材用途"] = task["需求属性"] || task["素材用途"] || "代投";
            orderedData["投放渠道"] = mediaChannel;
            orderedData["素材类型"] = "平面-买量素材-奇觅";
            orderedData["原创"] = rawMaterialCount;
            // 尺寸延展 = 所有尺寸的所需数量之和
            const totalExt = details.reduce((acc, d) => acc + (parseInt(d.requiredQuantity) || 0), 0);
            orderedData["尺寸延展"] = totalExt || (rawMaterialCount * details.length);
        } else {
            // 视频模板 (13个字段)
            orderedData["日期"] = dateStr;
            orderedData["制作人"] = makerName;
            orderedData["项目名称"] = gameName;
            orderedData["公司名称"] = companyName;
            orderedData["集团"] = companyName;
            orderedData["设计小组"] = "AIGC组";
            orderedData["需求归属"] = "移动终端-IAA";
            orderedData["需求属性"] = "代投";
            orderedData["渠道"] = mediaChannel;
            orderedData["素材类型"] = "视频";
            orderedData["工具标签"] = "奇觅";
            orderedData["视频总产出"] = String(rawMaterialCount);
            orderedData["原创视频"] = rawMaterialCount;
        }

        // 收集附加属性（包含项目全名）
        const extraAttributesMap = { "项目全称": fullName };
        const skipKeys = new Set([
            "日期", "制作人", "项目游戏名称", "项目名称", "项目全称", "projectName",
            "公司名称", "公司主体", "集团", "集团名称", "设计小组", "需求归属",
            "需求属性", "渠道", "投放媒体", "素材类型", "materialType", "工具标签",
            "视频总产出", "原创视频", "所需套数", "素材数", "原创", "尺寸延展",
            "网易标识", "广告策略", "素材用途", "投放渠道", "业务分类", "需求方",
            "details", "尺寸要求明细"
        ]);

        Object.keys(task).forEach(k => {
            if (!skipKeys.has(k)) {
                extraAttributesMap[k] = task[k];
            }
        });

        // 组装格式化的尺寸明细
        const cleanDetails = details.map(d => {
            return {
                "版位类型": d.positionType || (isGraphic ? "平面" : "视频"),
                "分辨率": d.resolution,
                "大小限制": d.sizeLimit,
                "所需数量": String(d.requiredQuantity)
            };
        });
        
        orderedData["尺寸要求明细"] = cleanDetails;
        orderedData["其他信息"] = extraAttributesMap;

        return orderedData;
    });

    // 导出文件
    const jsonStr = JSON.stringify(formattedDataList, null, 2);
    const blob = new Blob([jsonStr], {type: "application/json;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    
    // 按照指定格式命名：yyyymmdd-制作人名字数据表.json
    const d = new Date();
    const yyyymmdd = d.getFullYear() + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0');
    const finalMakerName = formattedDataList.length > 0 ? formattedDataList[0]["制作人"] : "孟祥伟";
    const fileName = `${yyyymmdd}-${finalMakerName}数据表.json`;

    chrome.downloads.download({ url: url, filename: fileName });
});
    
// 4. 导出 Excel 功能
document.getElementById('exportExcelBtn').addEventListener('click', async () => {
    if (!extractedBulkData || extractedBulkData.length === 0) {
        alert("没有可导出的数据！");
        return;
    }

    if (typeof XLSX === 'undefined') {
        alert("Excel 导出库未加载，请刷新插件后重试！");
        return;
    }

    const graphicHeaders = ["日期", "制作人", "项目名称", "公司名称", "集团", "需求方", "网易标识", "业务分类", "广告策略", "素材用途", "投放渠道", "素材类型", "原创", "尺寸延展"];
    const videoHeaders = ["日期", "制作人", "项目名称", "公司名称", "集团", "设计小组", "需求归属", "需求属性", "渠道", "素材类型", "工具标签", "视频总产出", "原创视频"];

    const splitProjectName = (fullName, company, channel) => {
        if (!fullName) return "未知项目";
        const parts = fullName.split('-');
        if (parts.length <= 1) return fullName;
        if (parts.length === 2) return parts[1].trim();

        const knownChannels = ["华为", "穿山甲", "广点通", "快手", "腾讯", "抖音", "头条", "oppo", "vivo", "小米", "百度", "b站", "微信", "朋友圈", "优量汇", "巨量", "巨量引擎", "苹果", "ios", "安卓", "android"];
        const commonTags = ["手动", "自动", "竖版", "横版", "测试", "常规", "首发", "图文", "视频", "平面", "自投", "代投"];

        let candidates = parts.slice(1).filter(p => {
            const pt = p.trim().toLowerCase();
            if (channel && pt === channel.toLowerCase()) return false;
            if (company && pt === company.toLowerCase()) return false;
            if (company && pt.includes(company.toLowerCase())) return false;
            if (knownChannels.includes(pt)) return false;
            if (commonTags.includes(pt)) return false;
            if (/^\d{4}$/.test(pt) || /^\d{6}$/.test(pt) || /^\d{8}$/.test(pt)) return false;
            return true;
        });

        if (candidates.length > 0) {
            candidates.sort((a, b) => b.trim().length - a.trim().length);
            return candidates[0].trim();
        }

        return parts[1].trim();
    };

    const getTaskExportBase = (task) => {
        const today = new Date();
        const dateStr = today.toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\//g, '/');
        const companyName = task["集团名称"] || task["公司名称"] || task["公司主体"] || "赛诺斯";
        const mediaChannel = task["投放媒体"] || task["渠道"] || "华为";
        const gameName = splitProjectName(task.projectName || task["项目名称"], companyName, mediaChannel);

        let rawMaterialCount = 4;
        const rawSets = task["所需套数"] || task["素材数"];
        if (rawSets) {
            const match = String(rawSets).match(/\d+/);
            if (match) rawMaterialCount = parseInt(match[0], 10);
        }

        return {
            dateStr,
            companyName,
            mediaChannel,
            gameName,
            rawMaterialCount,
            makerName: task["制作人"] || task["制作者"] || "制作人",
            details: task.details || []
        };
    };

    const createBorder = () => ({
        top: { style: "thin", color: { rgb: "D0D7E5" } },
        bottom: { style: "thin", color: { rgb: "D0D7E5" } },
        left: { style: "thin", color: { rgb: "D0D7E5" } },
        right: { style: "thin", color: { rgb: "D0D7E5" } }
    });

    const createAlignment = () => ({
        wrapText: true,
        horizontal: "center",
        vertical: "center"
    });

    const createHeaderStyle = () => ({
        fill: { patternType: "solid", fgColor: { rgb: "2F75B5" } },
        font: { color: { rgb: "FFFFFF" }, bold: true },
        border: createBorder(),
        alignment: createAlignment()
    });

    const createDataCellStyle = (header) => {
        const style = {
            border: createBorder(),
            alignment: createAlignment()
        };

        if (header === "项目名称") {
            style.fill = { patternType: "solid", fgColor: { rgb: "D9E1F2" } };
        }

        if (header === "投放渠道" || header === "渠道") {
            style.fill = { patternType: "solid", fgColor: { rgb: "FCE4D6" } };
        }

        if (["原创", "尺寸延展", "视频总产出", "原创视频"].includes(header)) {
            style.fill = { patternType: "solid", fgColor: { rgb: "E2EFDA" } };
            style.font = { bold: true };
        }

        return style;
    };

    const getColumnWidths = (headers) => {
        const widthMap = {
            "日期": 12,
            "制作人": 12,
            "项目名称": 25,
            "公司名称": 18,
            "集团": 18,
            "需求方": 16,
            "网易标识": 12,
            "业务分类": 16,
            "广告策略": 12,
            "素材用途": 14,
            "投放渠道": 14,
            "设计小组": 14,
            "需求归属": 14,
            "需求属性": 14,
            "渠道": 14,
            "素材类型": 18,
            "工具标签": 12,
            "原创": 12,
            "尺寸延展": 12,
            "视频总产出": 12,
            "原创视频": 12
        };

        return headers.map(header => ({ wch: widthMap[header] || 12 }));
    };

    const buildWorksheet = (headers, rows) => {
        const aoa = [
            headers,
            ...rows.map(row => headers.map(header => row[header] == null ? '' : String(row[header])))
        ];

        const ws = XLSX.utils.aoa_to_sheet(aoa);
        ws['!cols'] = getColumnWidths(headers);
        ws['!rows'] = Array.from({ length: aoa.length }, (_, index) => {
            return index === 0 ? { hpx: 28 } : { hpx: 24 };
        });

        headers.forEach((header, colIndex) => {
            const cellAddress = XLSX.utils.encode_cell({ r: 0, c: colIndex });
            if (ws[cellAddress]) {
                ws[cellAddress].s = createHeaderStyle();
            }
        });

        for (let rowIndex = 1; rowIndex < aoa.length; rowIndex += 1) {
            headers.forEach((header, colIndex) => {
                const cellAddress = XLSX.utils.encode_cell({ r: rowIndex, c: colIndex });
                if (ws[cellAddress]) {
                    ws[cellAddress].s = createDataCellStyle(header);
                }
            });
        }

        return ws;
    };

    const downloadWorkbook = (wb, fileName) => {
        const workbookArray = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
        const blob = new Blob([workbookArray], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
        const url = URL.createObjectURL(blob);

        return new Promise((resolve, reject) => {
            chrome.downloads.download({ url, filename: fileName }, (downloadId) => {
                const runtimeError = chrome.runtime.lastError;
                setTimeout(() => URL.revokeObjectURL(url), 1000);

                if (runtimeError) {
                    reject(new Error(runtimeError.message));
                    return;
                }

                resolve(downloadId);
            });
        });
    };

    const graphicTasks = [];
    const videoTasks = [];

    extractedBulkData.forEach(task => {
        const materialType = task.materialType || task["素材类型"] || "";
        if (materialType.includes("平面")) {
            graphicTasks.push(task);
        } else if (materialType.includes("视频")) {
            videoTasks.push(task);
        }
    });

    if (graphicTasks.length === 0 && videoTasks.length === 0) {
        alert("没有可导出的平面或视频任务！");
        return;
    }

    const now = new Date();
    const yyyymmdd = now.getFullYear() + String(now.getMonth() + 1).padStart(2, '0') + String(now.getDate()).padStart(2, '0');

    try {
        if (graphicTasks.length > 0) {
            const graphicRows = graphicTasks.map(task => {
                const { dateStr, companyName, mediaChannel, gameName, rawMaterialCount, makerName, details } = getTaskExportBase(task);
                const totalExt = details.reduce((acc, d) => acc + (parseInt(d.requiredQuantity, 10) || 0), 0) || (rawMaterialCount * details.length);

                return {
                    "日期": dateStr,
                    "制作人": makerName,
                    "项目名称": gameName,
                    "公司名称": companyName,
                    "集团": companyName,
                    "需求方": task["需求方"] || "移动终端事业部",
                    "网易标识": "非网易",
                    "业务分类": task["需求归属"] || task["业务分组"] || "移动终端-IAA",
                    "广告策略": "竞价",
                    "素材用途": task["需求属性"] || task["素材用途"] || "代投",
                    "投放渠道": mediaChannel,
                    "素材类型": "平面-买量素材-奇觅",
                    "原创": rawMaterialCount,
                    "尺寸延展": totalExt
                };
            });

            const graphicSheet = buildWorksheet(graphicHeaders, graphicRows);
            const graphicWorkbook = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(graphicWorkbook, graphicSheet, "平面报表");
            const graphicMakerName = graphicRows[0]["制作人"] || "制作人";
            await downloadWorkbook(graphicWorkbook, `${yyyymmdd}-${graphicMakerName}-平面报表.xlsx`);
        }

        if (videoTasks.length > 0) {
            const videoRows = videoTasks.map(task => {
                const { dateStr, companyName, mediaChannel, gameName, rawMaterialCount, makerName } = getTaskExportBase(task);

                return {
                    "日期": dateStr,
                    "制作人": makerName,
                    "项目名称": gameName,
                    "公司名称": companyName,
                    "集团": companyName,
                    "设计小组": "AIGC组",
                    "需求归属": task["需求归属"] || "移动终端-IAA",
                    "需求属性": task["需求属性"] || "代投",
                    "渠道": mediaChannel,
                    "素材类型": "视频",
                    "工具标签": "奇觅",
                    "视频总产出": String(rawMaterialCount),
                    "原创视频": rawMaterialCount
                };
            });

            const videoSheet = buildWorksheet(videoHeaders, videoRows);
            const videoWorkbook = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(videoWorkbook, videoSheet, "视频报表");
            const videoMakerName = videoRows[0]["制作人"] || "制作人";
            await downloadWorkbook(videoWorkbook, `${yyyymmdd}-${videoMakerName}-视频报表.xlsx`);
        }
    } catch (err) {
        console.error("生成 Excel 失败:", err);
        alert("生成 Excel 文件失败：" + err.message);
    }
});
