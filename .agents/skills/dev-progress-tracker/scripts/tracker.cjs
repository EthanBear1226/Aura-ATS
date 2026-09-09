const fs = require('fs');
const path = require('path');
const os = require('os');

const AUTHOR = 'EthanBear1226';

const NAMES_LIBRARY = {
  constellations: [
    { en: 'Orion', cn: '猎户座' },
    { en: 'Lyra', cn: '天琴座' },
    { en: 'Cygnus', cn: '天鹅座' },
    { en: 'Pegasus', cn: '飞马座' },
    { en: 'Cassiopeia', cn: '仙后座' }
  ],
  animals: [
    { en: 'Snow Leopard', cn: '雪豹' },
    { en: 'Golden Eagle', cn: '金雕' },
    { en: 'Arctic Wolf', cn: '北极狼' },
    { en: 'Pacific Whale', cn: '太平洋鲸鱼' },
    { en: 'Red Panda', cn: '小熊猫' }
  ],
  places: [
    { en: 'Serengeti', cn: '塞伦盖蒂' },
    { en: 'Aurora', cn: '欧若拉' },
    { en: 'Olympus', cn: '奥林匹斯' },
    { en: 'Amazon', cn: '亚马逊' },
    { en: 'Sahara', cn: '撒哈拉' }
  ],
  people: [
    { en: 'Socrates', cn: '苏格拉底' },
    { en: 'Da Vinci', cn: '达芬奇' },
    { en: 'Tesla', cn: '特斯拉' },
    { en: 'Curie', cn: '居里夫人' },
    { en: 'Newton', cn: '牛顿' }
  ]
};

function getRandomName() {
  const categories = Object.keys(NAMES_LIBRARY);
  const cat = categories[Math.floor(Math.random() * categories.length)];
  const names = NAMES_LIBRARY[cat];
  const item = names[Math.floor(Math.random() * names.length)];
  const enFormatted = item.en.replace(/\s+/g, '-');
  return `${enFormatted}-(${item.cn})`;
}

/**
 * 获取北京时间 (UTC+8) 的时间戳
 */
function getTimestamp() {
  const now = new Date();
  const utc8Time = new Date(now.getTime() + 8 * 60 * 60 * 1000);
  return utc8Time.toISOString().replace('T', ' ').substring(0, 19);
}

/**
 * 向上级目录递归查找 Progress_*.md 或 PROGRESS.md，防止在子目录执行时产生重复文件
 */
function findLogFile() {
  let currentDir = process.cwd();
  let rootDir = currentDir;
  let logFile = null;

  while (true) {
    if (fs.existsSync(currentDir)) {
      const files = fs.readdirSync(currentDir);
      
      // 优先匹配标准格式无哈希后缀的 Progress_*.md，再匹配带哈希的，最后匹配 PROGRESS.md
      let found = files.find(f => /^Progress_[^-\n]+-\([^)\n]+\)\.md$/.test(f)) || files.find(f => /^Progress_.+\.md$/.test(f));
      if (!found) {
        found = files.find(f => /^PROGRESS\.md$/i.test(f));
      }

      if (found) {
        logFile = path.join(currentDir, found);
        rootDir = currentDir; 
        // 既然找到了日志文件，通常这里就是项目的逻辑根目录，可以直接返回
        break;
      }

      // 即使没找到日志，如果发现了项目标识文件，也记录下这个潜在的根目录
      if (files.includes('.git') || files.includes('package.json') || files.includes('dev-progress-tracker.skill') || files.includes('design.md')) {
        rootDir = currentDir;
      }
    }

    const parentDir = path.dirname(currentDir);
    // 只有退到了文件系统根目录才停止查找
    if (parentDir === currentDir) {
      break;
    }
    currentDir = parentDir;
  }

  return { logFile, rootDir };
}

function updateProgress() {
  const args = process.argv.slice(2);
  const taskIdx = args.indexOf('--task');
  const decisionIdx = args.indexOf('--decision');
  const stageIdx = args.indexOf('--stage');

  const task = taskIdx !== -1 ? args[taskIdx + 1] : null;
  const decision = decisionIdx !== -1 ? args[decisionIdx + 1] : null;
  const stage = stageIdx !== -1 ? args[stageIdx + 1] : null;

  let content = '';
  let projectName = '';
  let version = 'v1.0.0';
  let { logFile, rootDir } = findLogFile();

  if (logFile && fs.existsSync(logFile)) {
    content = fs.readFileSync(logFile, 'utf8');
    
    // 向下兼容逻辑：如果是旧的 PROGRESS.md，则重命名它
    if (/^PROGRESS\.md$/i.test(path.basename(logFile))) {
       projectName = getRandomName();
       const newLogFile = path.join(rootDir, `Progress_${projectName}.md`);
       fs.renameSync(logFile, newLogFile);
       logFile = newLogFile; 
       
       if (content.includes('# 🚀 开发进展')) {
         content = content.replace(/# 🚀 开发进展.*/, `# 🚀 开发进展：${projectName}`);
       }
    }

    const headerMatch = content.match(/# 🚀 开发进展：(.*)/);
    if (headerMatch) projectName = headerMatch[1].trim();

    const versionMatch = content.match(/v(\d+)\.(\d+)\.(\d+)/);
    if (versionMatch) {
      let [full, x, y, z] = versionMatch;
      if (stage) {
        y = parseInt(y) + 1;
        z = 0;
      } else {
        z = parseInt(z) + 1;
      }
      version = `v${x}.${y}.${z}`;
    }
  } else {
    projectName = getRandomName();
    logFile = path.join(rootDir, `Progress_${projectName}.md`);
  }

  const fullVersion = `${projectName}-${version}`;
  const timestamp = getTimestamp();

  let newEntry = '';
  if (task) {
    newEntry += `- **${version}**: ${task} (${timestamp})\n`;
  }

  let updatedContent = '';
  if (!fs.existsSync(logFile)) {
    updatedContent = `# 🚀 开发进展：${projectName}\n` +
                     `- **主负责人**: ${AUTHOR}\n` +
                     `- **当前版本**: ${fullVersion}\n\n` +
                     `## 📝 阶段概览\n> 当前状态：${stage || '初始化项目'}\n\n` +
                     `## 📈 变更流 (Timeline)\n${newEntry}\n` +
                     `## 📌 决策记录\n${decision ? `- [${timestamp}] ${decision}\n` : ''}`;
  } else {
    updatedContent = content.replace(/- \*\*当前版本\*\*: .*/, `- **当前版本**: ${fullVersion}`);
    
    if (stage) {
      updatedContent = updatedContent.replace(/> 当前状态：.*/, `> 当前状态：${stage}`);
    }

    if (task) {
      if (updatedContent.match(/## 📈 变更流 \(Timeline\)\n/)) {
        updatedContent = updatedContent.replace(/## 📈 变更流 \(Timeline\)\n/, `## 📈 变更流 (Timeline)\n${newEntry}`);
      } else {
        updatedContent = updatedContent.replace(/## 📌 决策记录/, `## 📈 变更流 (Timeline)\n${newEntry}\n\n## 📌 决策记录`);
      }
    }

    if (decision) {
      if (!updatedContent.includes('## 📌 决策记录')) {
          updatedContent += `\n## 📌 决策记录\n- [${timestamp}] ${decision}\n`;
      } else {
          updatedContent += `- [${timestamp}] ${decision}\n`;
      }
    }
  }

  fs.writeFileSync(logFile, updatedContent);
  console.log(`✅ Progress updated in ${logFile} to ${fullVersion}`);
}

updateProgress();
