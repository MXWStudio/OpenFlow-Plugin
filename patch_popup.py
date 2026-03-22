import sys

file_path = 'c:/Users/mxw86/Documents/openflow-plugin/popup.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content_normalized = content.replace('\r\n', '\n')

old_func1 = """    // 助手函数：拆分项目名称，提取游戏名
    const splitProjectName = (fullName) => {
        if (!fullName) return { gameName: "未知项目", fullName: "未知项目" };
        // 一般格式：赛诺斯-小火车呜呜呜-华为-0304 或 赛诺斯-小火车呜呜呜
        const parts = fullName.split('-');
        if (parts.length >= 2) {
            return { gameName: parts[1].trim(), fullName: fullName };
        }
        return { gameName: fullName, fullName: fullName };
    };"""
new_func1 = """    // 助手函数：拆分项目名称，提取游戏名，灵活过滤冗余信息
    const splitProjectName = (fullName, company, channel) => {
        if (!fullName) return { gameName: "未知项目", fullName: "未知项目" };
        const parts = fullName.split('-');
        if (parts.length <= 1) return { gameName: fullName, fullName: fullName };
        if (parts.length === 2) return { gameName: parts[1].trim(), fullName: fullName };

        const knownChannels = ["华为", "穿山甲", "广点通", "快手", "腾讯", "抖音", "头条", "oppo", "vivo", "小米", "百度", "b站", "微信", "朋友圈", "优量汇", "巨量", "巨量引擎", "苹果", "ios", "安卓", "android"];

        let candidates = parts.slice(1).filter(p => {
            const pt = p.trim().toLowerCase();
            if (channel && pt === channel.toLowerCase()) return false;
            if (company && pt === company.toLowerCase()) return false;
            if (company && pt.includes(company.toLowerCase())) return false;
            if (knownChannels.includes(pt)) return false;
            if (/^\\d{4}$/.test(pt) || /^\\d{6}$/.test(pt) || /^\\d{8}$/.test(pt)) return false;
            return true;
        });

        if (candidates.length > 0) {
            return { gameName: candidates.map(c => c.trim()).join('-'), fullName: fullName };
        }
        
        return { gameName: parts[1].trim(), fullName: fullName };
    };"""

content_normalized = content_normalized.replace(old_func1, new_func1)

old_map = """    // 按目标结构重建 JSON 列表
    const formattedDataList = extractedBulkData.map(task => {
        const orderedData = {};
        const { gameName, fullName } = splitProjectName(task.projectName || task["项目名称"]);
        
        // 日期处理
        const today = new Date();
        const dateStr = today.toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\\//g, '/');
        
        // 核心值
        // 公司名称和集团：直接使用网页动态提取的“集团名称”字段，保证与系统完全一致
        const companyName = task["集团名称"] || task["公司名称"] || task["公司主体"] || "赛诺斯";
        const mediaChannel = task["投放媒体"] || task["渠道"] || "华为";"""
new_map = """    // 按目标结构重建 JSON 列表
    const formattedDataList = extractedBulkData.map(task => {
        const orderedData = {};

        // 公司名称和集团需要提前获取用于项目名清洗
        const companyName = task["集团名称"] || task["公司名称"] || task["公司主体"] || "赛诺斯";
        const mediaChannel = task["投放媒体"] || task["渠道"] || "华为";

        const { gameName, fullName } = splitProjectName(task.projectName || task["项目名称"], companyName, mediaChannel);
        
        // 日期处理
        const today = new Date();
        const dateStr = today.toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\\//g, '/');
        
        // 核心值"""

content_normalized = content_normalized.replace(old_map, new_map)

old_func2 = """        // 助手函数：拆分项目名称
        const splitProjectName = (fullName) => {
            if (!fullName) return "未知项目";
            const parts = fullName.split('-');
            return parts.length >= 2 ? parts[1].trim() : fullName;
        };"""
new_func2 = """        // 助手函数：拆分项目名称，灵活提取
        const splitProjectName = (fullName, company, channel) => {
            if (!fullName) return "未知项目";
            const parts = fullName.split('-');
            if (parts.length <= 1) return fullName;
            if (parts.length === 2) return parts[1].trim();

            const knownChannels = ["华为", "穿山甲", "广点通", "快手", "腾讯", "抖音", "头条", "oppo", "vivo", "小米", "百度", "b站", "微信", "朋友圈", "优量汇", "巨量", "巨量引擎", "苹果", "ios", "安卓", "android"];

            let candidates = parts.slice(1).filter(p => {
                const pt = p.trim().toLowerCase();
                if (channel && pt === channel.toLowerCase()) return false;
                if (company && pt === company.toLowerCase()) return false;
                if (company && pt.includes(company.toLowerCase())) return false;
                if (knownChannels.includes(pt)) return false;
                if (/^\\d{4}$/.test(pt) || /^\\d{6}$/.test(pt) || /^\\d{8}$/.test(pt)) return false;
                return true;
            });

            if (candidates.length > 0) {
                return candidates.map(c => c.trim()).join('-');
            }

            return parts[1].trim();
        };"""
content_normalized = content_normalized.replace(old_func2, new_func2)

old_foreach = """        extractedBulkData.forEach(task => {
            const today = new Date();
            const dateStr = today.toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\\//g, '/');
            const gameName = splitProjectName(task.projectName || task["项目名称"]);
            
            // 公司名称和集团：直接使用网页动态提取的“集团名称”字段
            const companyName = task["集团名称"] || task["公司名称"] || task["公司主体"] || "赛诺斯";
            const mediaChannel = task["投放媒体"] || task["渠道"] || "华为";"""
new_foreach = """        extractedBulkData.forEach(task => {
            const today = new Date();
            const dateStr = today.toLocaleDateString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit'}).replace(/\\//g, '/');
            
            // 提取公司和渠道用于项目名过滤
            const companyName = task["集团名称"] || task["公司名称"] || task["公司主体"] || "赛诺斯";
            const mediaChannel = task["投放媒体"] || task["渠道"] || "华为";

            const gameName = splitProjectName(task.projectName || task["项目名称"], companyName, mediaChannel);"""
content_normalized = content_normalized.replace(old_foreach, new_foreach)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content_normalized)

print("Replacement successful")
