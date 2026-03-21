// popup.js
let extractedBulkData = [];

// 初始化：检查本地存储是否有上次提取的数据
document.addEventListener('DOMContentLoaded', () => {
    chrome.storage.local.get(['lastExtractedBulkData'], function(result) {
        if (result.lastExtractedBulkData && result.lastExtractedBulkData.length > 0) {
            extractedBulkData = result.lastExtractedBulkData;
            renderPreview(extractedBulkData);
        }
    });
});

document.getElementById('extractBtn').addEventListener('click', async () => {
    const btn = document.getElementById('extractBtn');
    
    // 1. 按钮防抖与提示交互
    btn.disabled = true;
    btn.innerText = "正在自动点击抓取中，请勿操作网页...";
    document.getElementById('previewArea').style.display = 'none';

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
            chrome.tabs.sendMessage(tab.id, { action: "EXTRACT_BULK_DOM" }, (response) => {
                // 恢复按钮状态
                btn.disabled = false;
                btn.innerText = '提取所有"未开始"任务';

                if (chrome.runtime.lastError) {
                    alert("无法连接到页面脚本，请刷新页面后重试。\n错误信息: " + chrome.runtime.lastError.message);
                    return;
                }

                if (response && response.success) {
                    extractedBulkData = response.data || [];
                    if (extractedBulkData.length === 0) {
                        alert("未找到任何状态为“未开始”的任务！");
                    } else {
                        // 将数据保存到本地存储
                        chrome.storage.local.set({ 'lastExtractedBulkData': extractedBulkData }, function() {
                            console.log('数据已保存到本地存储。');
                        });
                        renderPreview(extractedBulkData);
                    }
                } else {
                    alert("提取失败！\n" + (response?.error || '未知错误'));
                }
            });
        }, 150);
        
    } catch (err) {
        btn.disabled = false;
        btn.innerText = '提取所有"未开始"任务';
        alert("执行脚本发生错误：" + err.message);
    }
});

/**
 * 渲染预览界面
 */
function renderPreview(dataList) {
    document.getElementById('previewArea').style.display = 'block';
    
    // 统计平面、视频和未知任务的数量
    let graphicCount = 0;
    let videoCount = 0;
    let unknownCount = 0;

    dataList.forEach(task => {
        const materialTypeRaw = task.materialType || task["素材类型"] || "";
        if (materialTypeRaw.includes("平面")) {
            graphicCount++;
        } else if (materialTypeRaw.includes("视频")) {
            videoCount++;
        } else {
            unknownCount++;
        }
    });

    let statusMsg = `提取完成！共计 ${dataList.length} 个任务。`;
    let typeMsgParts = [];
    if (graphicCount > 0) typeMsgParts.push(`平面：${graphicCount}`);
    if (videoCount > 0) typeMsgParts.push(`视频：${videoCount}`);
    if (unknownCount > 0) typeMsgParts.push(`未知任务：${unknownCount}`);

    if (typeMsgParts.length > 0) {
        statusMsg += ` (${typeMsgParts.join('  ')})`;
    }

    // 显示成功提取的任务数量及类型统计
    document.getElementById('statusText').innerText = statusMsg;
    
    const ul = document.getElementById('taskList');
    ul.innerHTML = '';
    
    // 简要展示每个任务的名称和尺寸数量
    dataList.forEach(task => {
        let li = document.createElement('li');
        
        // 项目名称
        let nameSpan = document.createElement('span');
        nameSpan.className = 'name';
        nameSpan.innerText = task.projectName || '未知项目';
        nameSpan.title = task.projectName; // 鼠标悬浮显示完整名称
        
        // 尺寸数量
        let countSpan = document.createElement('span');
        countSpan.className = 'count';
        const detailsCount = task.details ? task.details.length : 0;
        countSpan.innerText = `${detailsCount} 个尺寸`;

        li.appendChild(nameSpan);
        li.appendChild(countSpan);
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
    
    // 助手函数：拆分项目名称，提取游戏名
    const splitProjectName = (fullName) => {
        if (!fullName) return { gameName: "未知项目", fullName: "未知项目" };
        // 一般格式：赛诺斯-小火车呜呜呜-华为-0304 或 赛诺斯-小火车呜呜呜
        const parts = fullName.split('-');
        if (parts.length >= 2) {
            return { gameName: parts[1].trim(), fullName: fullName };
        }
        return { gameName: fullName, fullName: fullName };
    };

    // 按目标结构重建 JSON 列表
    const formattedDataList = extractedBulkData.map(task => {
        const orderedData = {};
        const { gameName, fullName } = splitProjectName(task.projectName || task["项目名称"]);
        
        // 日期处理
        const today = new Date();
        const dateStr = today.toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\//g, '/');
        
        // 核心值
        // 公司名称和集团：直接使用网页动态提取的“集团名称”字段，保证与系统完全一致
        const companyName = task["集团名称"] || task["公司名称"] || task["公司主体"] || "赛诺斯";
        const mediaChannel = task["投放媒体"] || task["渠道"] || "华为";
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
    
// 4. 导出 CSV 功能
document.getElementById('exportCsvBtn').addEventListener('click', () => {
    if (!extractedBulkData || extractedBulkData.length === 0) {
        alert("没有可导出的数据！");
        return;
    }

    try {
        // 判断第一项的任务类型来决定表头
        const firstTask = extractedBulkData[0];
        const materialTypeRaw = firstTask.materialType || firstTask["素材类型"] || "";
        const isGraphic = materialTypeRaw.includes("平面");

        let headers = [];
        if (isGraphic) {
            headers = ["日期", "制作人", "项目名称", "公司名称", "集团", "需求方", "网易标识", "业务分类", "广告策略", "素材用途", "投放渠道", "素材类型", "原创", "尺寸延展"];
        } else {
            headers = ["日期", "制作人", "项目名称", "公司名称", "集团", "设计小组", "需求归属", "需求属性", "渠道", "素材类型", "工具标签", "视频总产出", "原创视频"];
        }

        let csvContent = "\uFEFF"; // 添加 BOM 头
        csvContent += headers.join(",") + "\n";

        // 助手函数：拆分项目名称
        const splitProjectName = (fullName) => {
            if (!fullName) return "未知项目";
            const parts = fullName.split('-');
            return parts.length >= 2 ? parts[1].trim() : fullName;
        };

        extractedBulkData.forEach(task => {
            const today = new Date();
            const dateStr = today.toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\//g, '/');
            const gameName = splitProjectName(task.projectName || task["项目名称"]);
            
            // 公司名称和集团：直接使用网页动态提取的“集团名称”字段
            const companyName = task["集团名称"] || task["公司名称"] || task["公司主体"] || "赛诺斯";
            const mediaChannel = task["投放媒体"] || task["渠道"] || "华为";

            let rawMaterialCount = 4;
            const rawSets = task["所需套数"] || task["素材数"];
            if (rawSets) {
                const match = String(rawSets).match(/\d+/);
                if (match) rawMaterialCount = parseInt(match[0], 10);
            }
            
            const makerName = task["制作人"] || task["制作者"] || "孟祥伟";

            let row = [];
            if (isGraphic) {
                const details = task.details || [];
                const totalExt = details.reduce((acc, d) => acc + (parseInt(d.requiredQuantity) || 0), 0) || (rawMaterialCount * details.length);
                row = [
                    dateStr, makerName, gameName, companyName, companyName,
                    task["需求方"] || "移动终端事业部", "非网易",
                    task["需求归属"] || task["业务分组"] || "移动终端-IAA", "竞价",
                    task["需求属性"] || task["素材用途"] || "代投", mediaChannel,
                    "平面-买量素材-奇觅", rawMaterialCount, totalExt
                ];
            } else {
                row = [
                    dateStr, makerName, gameName, companyName, companyName,
                    "AIGC组", "移动终端-IAA", "代投", mediaChannel,
                    "视频", "奇觅", rawMaterialCount, rawMaterialCount
                ];
            }

            const escapedRow = row.map(val => `"${String(val).replace(/"/g, '""')}"`);
            csvContent += escapedRow.join(",") + "\n";
        });

        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const d = new Date();
        const yyyymmdd = d.getFullYear() + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0');
        const csvMakerName = extractedBulkData.length > 0 ? (extractedBulkData[0]["制作人"] || extractedBulkData[0]["制作者"] || "制作人") : "制作人";
        const fileName = `${yyyymmdd}-${csvMakerName}-报表.csv`;
        
        chrome.downloads.download({ url: url, filename: fileName });
        
    } catch (err) {
        console.error("生成 CSV 失败:", err);
        alert("生成 CSV 文件失败：" + err.message);
    }
});
