// popup.js
let extractedData = null;

document.getElementById('extractBtn').addEventListener('click', async () => {
  // 获取当前活动标签页
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  // 注入 content.js (如果尚未注入) 并发送消息
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ['content.js']
  }, () => {
    // 延迟一点时间确保 content.js 加载解析完毕并注册好 listener
    setTimeout(() => {
        chrome.tabs.sendMessage(tab.id, { action: "EXTRACT_DOM" }, (response) => {
          if (chrome.runtime.lastError) {
             alert("无法连接到页面脚本，请刷新页面后重试。\n错误信息: " + chrome.runtime.lastError.message);
             return;
          }
          if (response && response.success) {
            extractedData = response.data;
            renderPreview(extractedData);
          } else {
            alert("提取失败或未找到匹配数据节点！\n" + (response?.error || '未知错误'));
          }
        });
    }, 100);
  });
});

// 渲染预览界面
function renderPreview(data) {
  document.getElementById('previewArea').style.display = 'block';
  document.getElementById('pName').innerText = data["项目游戏名称"];
  document.getElementById('pType').innerText = data["素材类型"];
  
  const ul = document.getElementById('pDetails');
  ul.innerHTML = '';
  let folderTreeStr = `${data["项目游戏名称"]}/\n`;
  
  data["尺寸要求明细"].forEach(item => {
    let li = document.createElement('li');
    li.innerText = `${item["版位类型"]} - ${item["分辨率"]} (${item["所需数量"]}个)`;
    ul.appendChild(li);
    
    // 生成文件夹树预览
    folderTreeStr += ` ├── ${item["分辨率"]}/\n`;
  });
  folderTreeStr += ` ├── config.json\n └── 需求明细.xlsx\n`;
  document.getElementById('folderPreview').innerText = folderTreeStr;
}

// 下载 JSON
document.getElementById('downloadJsonBtn').addEventListener('click', () => {
  if(!extractedData) return;
  const orderedData = {};
  
  const pName = extractedData["项目游戏名称"] || "未知项目";
  const pType = extractedData["素材类型"] || "未知";
  const dateStr = new Date().toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\//g, '/');

  const maker = extractedData["制作人"] || extractedData["制作者"] || "";
  const group = extractedData["集团名称"] || "";
  const company = extractedData["公司主体"] || extractedData["公司名称"] || group; 
  const demander = extractedData["需求方"] || "移动终端事业部";
  const bizGroup = extractedData["业务分组"] || "移动终端-IAA";
  const adStrategy = extractedData["广告策略"] || "竞价";
  const materialUsage = extractedData["素材用途"] || "代投";
  const channel = extractedData["投放媒体"] || "";
  const assignee = extractedData["业务承接"] || "AIGC组";

  let originalRaw = extractedData["素材数"] || extractedData["原创套数"];
  let originalCount = "";
  if (originalRaw) {
      const match = String(originalRaw).match(/\d+/);
      if (match) {
          originalCount = parseInt(match[0], 10);
      }
  }
  if (originalCount === 0 || originalCount === "") { originalCount = ""; }

  const details = extractedData["尺寸要求明细"] || [];
  let totalExtended = 0;
  details.forEach(item => {
      const count = parseInt(item["所需数量"], 10) || 0;
      totalExtended += count;
  });

  if (pType.includes('平面')) {
      orderedData["日期"] = dateStr;
      orderedData["制作者"] = maker;
      orderedData["项目名称"] = pName;
      orderedData["公司主体"] = company;
      orderedData["集团"] = group;
      orderedData["需求方"] = demander;
      orderedData["网易标识"] = "";
      orderedData["业务分类"] = bizGroup;
      orderedData["广告策略"] = adStrategy;
      orderedData["素材用途"] = materialUsage;
      orderedData["投放渠道"] = channel;
      orderedData["素材类型"] = "平面-买量素材-奇觅";
      orderedData["原创"] = originalCount;
      orderedData["尺寸延展"] = totalExtended;
  } else {
      let originalCalc = originalCount === "" ? 0 : parseInt(originalCount, 10);
      let totalOutput = originalCalc + totalExtended;
      
      orderedData["日期"] = dateStr;
      orderedData["制作人"] = maker;
      orderedData["项目名称"] = pName;
      orderedData["公司名称"] = company;
      orderedData["集团"] = group;
      orderedData["设计小组"] = "AIGC组";
      orderedData["需求归属"] = "移动终端-IAA";
      orderedData["需求属性"] = "代投"; // 固定值
      orderedData["渠道"] = channel;
      orderedData["素材类型"] = "视频";
      orderedData["工具标签"] = "奇觅";
      orderedData["视频总产出"] = totalOutput;
      orderedData["原创视频"] = originalCount;
      orderedData["素材用途"] = materialUsage;
  }

  // 将剩余键按字母序排列
  const processedKeys = new Set([
      "日期", "制作人", "制作者", "项目游戏名称", "项目名称", "公司主体", "公司名称", "集团名称", "集团",
      "设计小组", "需求归属", "需求属性", "渠道", "投放媒体", "素材类型", "工具标签", 
      "视频总产出", "原创视频", "原创", "素材数", "原创套数", "尺寸延展", "需求方", 
      "网易标识", "业务分类", "广告策略", "素材用途", "投放渠道", "尺寸要求明细"
  ]);

  const remainingKeys = Object.keys(extractedData)
      .filter(k => !processedKeys.has(k))
      .sort((a, b) => a.localeCompare(b, 'zh'));

  remainingKeys.forEach(k => {
      orderedData[k] = extractedData[k];
  });

  // 最后附上尺寸列表
  orderedData["尺寸要求明细"] = details;

  const jsonStr = JSON.stringify(orderedData, null, 2);
  const blob = new Blob([jsonStr], {type: "application/json;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  
  const safeFilename = pName.replace(/[<>:"/\\|?*]/g, "");
  chrome.downloads.download({ url: url, filename: `${safeFilename}.json` });
});

// 下载 CSV
document.getElementById('downloadCsvBtn').addEventListener('click', () => {
  if(!extractedData) return;
  const pName = extractedData["项目游戏名称"] || "未知项目";
  const pType = extractedData["素材类型"] || "未知";
  const details = extractedData["尺寸要求明细"] || [];
  
  // 从动态抓取的数据中取值
  const maker = extractedData["制作人"] || extractedData["制作者"] || "";
  const group = extractedData["集团名称"] || "";
  const company = extractedData["公司主体"] || extractedData["公司名称"] || group; // 若无直接公司名，拿集团名保底
  const demander = extractedData["需求方"] || "移动终端事业部"; // 若空则取默认
  const bizGroup = extractedData["业务分组"] || "移动终端-IAA";
  const adStrategy = extractedData["广告策略"] || "竞价";
  const materialUsage = extractedData["素材用途"] || "代投";
  const channel = extractedData["投放媒体"] || "";
  const assignee = extractedData["业务承接"] || "AIGC组";
  
  // 原创套数 (优先从"素材数"中提取数字，如"4套"提取出4)
  let originalRaw = extractedData["素材数"] || extractedData["原创套数"];
  let originalCount = "";
  if (originalRaw) {
      const match = String(originalRaw).match(/\d+/);
      if (match) {
          originalCount = parseInt(match[0], 10);
      }
  }

  if (originalCount === 0 || originalCount === "") {
      originalCount = ""; // 留空让出表后自己填写，或者填默认
  }

  let csvContent = "\uFEFF"; // 添加 BOM 解决 Excel 中文乱码

  if (pType.includes('平面')) {
    // 平面格式 CSV 表头
    const headers = ["日期", "制作者", "项目名称", "公司主体", "集团", "需求方", "网易标识", "业务分类", "广告策略", "素材用途", "投放渠道", "素材类型", "原创", "尺寸延展"];
    csvContent += headers.join(",") + "\n";
    
    // 计算按规格的总延展套数
    let totalExtended = 0;
    details.forEach(item => {
        const count = parseInt(item["所需数量"], 10) || 0;
        totalExtended += count;
    });

    const dateStr = new Date().toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\//g, '/');
    
    // 生成单行数据：图1平面顺序
    const rowData = [
       dateStr, 
       maker, // 制作者
       pName,
       company, // 公司主体
       group, // 集团
       demander, // 需求方
       "", // 网易标识
       bizGroup, // 业务分类
       adStrategy, // 广告策略
       materialUsage, // 素材用途
       channel, // 投放渠道
       "平面-买量素材-奇觅", // 固定字段: 素材类型
       originalCount, // 原创
       totalExtended // 尺寸延展
    ];
    csvContent += rowData.join(",") + "\n";
    
  } else {
    // 默认按照 视频格式 CSV 表头
    const headers = ["日期", "制作人", "项目名称", "公司名称", "集团", "设计小组", "需求归属", "需求属性", "渠道", "素材类型", "工具标签", "视频总产出", "原创视频"];
    csvContent += headers.join(",") + "\n";

    let totalExtended = 0;
    details.forEach(item => {
        const count = parseInt(item["所需数量"], 10) || 0;
        totalExtended += count;
    });

    const dateStr = new Date().toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\//g, '/');
    
    // 视频总产出数据 = 素材数 (即原创视频的值)
    // 根据用户最新要求，“视频总产出”等于“素材数”的值，“原创视频”同理。
    let totalOutput = originalCount;

    // 生成单行数据：图2视频顺序
    const rowData = [
       dateStr, 
       maker, // 制作人
       pName,
       company, // 公司名称
       group, // 集团
       "AIGC组", // 设计小组 (固定值)
       "移动终端-IAA", // 需求归属 (固定值)
       "代投", // 需求属性 (固定值)
       channel, // 渠道 (投放媒体)
       "视频", // 固定字段: 素材类型
       "奇觅", // 固定字段: 工具标签
       totalOutput, // 视频总产出 = 素材数 (原创视频)
       originalCount // 原创视频
    ];
    csvContent += rowData.join(",") + "\n";
  }

  const blob = new Blob([csvContent], {type: "text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  
  // 以项目名称作为 CSV 名字
  const safeFilename = pName.replace(/[<>:"/\\|?*]/g, "");
  chrome.downloads.download({ url: url, filename: `${safeFilename}.csv` });
});
