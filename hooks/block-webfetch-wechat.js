#!/usr/bin/env node
/**
 * PreToolUse Hook: Block WebFetch for WeChat articles
 * Install: cp hooks/block-webfetch-wechat.js ~/.claude/hooks/
 */
let input = '';
process.stdin.on('data', d => input += d);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const url = data.tool_input && data.tool_input.url || '';
    if (url.includes('mp.weixin.qq.com')) {
      process.stdout.write(JSON.stringify({
        decision: 'block',
        reason: '禁止用 WebFetch 读取微信文章，请使用 ArticleContentFetcher (wechat-search skill)'
      }));
    }
  } catch (e) {}
});
