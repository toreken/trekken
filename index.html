<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>トレケン | トレンド研究所</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;700;900&family=Playfair+Display:wght@700;900&display=swap" rel="stylesheet">
  <style>
    :root {
      --brown-900: #2b1a0c;
      --brown-800: #3d2510;
      --brown-700: #5d3a1f;
      --brown-600: #704a2e;
      --brown-500: #8a5c3d;
      --brown-300: #c9a988;
      --brown-200: #e6d4be;
      --brown-100: #f1e3d0;
      --cream-50: #fdf9f3;
      --cream-100: #faf3e7;
      --cream-200: #f3e8d4;
      --gold-400: #d4a85a;
      --gold-500: #c49a4a;
      --gold-600: #a87f33;
      --ink: #2b1a0c;
      --muted: #7a6650;
      --line: #e6d4be;
      --shadow: 0 12px 40px rgba(60, 35, 15, 0.12);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    html { scroll-behavior: smooth; }

    body {
      min-height: 100vh;
      background:
        radial-gradient(ellipse at top left, var(--cream-100) 0%, transparent 50%),
        radial-gradient(ellipse at top right, #fbeacc 0%, transparent 50%),
        var(--cream-50);
      font-family: 'Noto Sans JP', sans-serif;
      color: var(--ink);
      overflow-x: hidden;
    }

    /* ===== 浮遊する装飾 ===== */
    .floaters { position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
    .floater { position: absolute; opacity: 0.35; }
    .floater.f1 { top: 8%; right: 6%; width: 90px; animation: float1 14s ease-in-out infinite; }
    .floater.f2 { top: 22%; left: 4%; width: 60px; animation: float2 18s ease-in-out infinite; }
    .floater.f3 { top: 50%; right: 12%; width: 70px; animation: float3 16s ease-in-out infinite; }
    .floater.f4 { top: 70%; left: 8%; width: 50px; animation: float1 20s ease-in-out infinite; }
    @keyframes float1 { 0%,100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-30px) rotate(15deg); } }
    @keyframes float2 { 0%,100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(25px) rotate(-12deg); } }
    @keyframes float3 { 0%,100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-20px) rotate(8deg); } }

    /* ===== ヘッダー（ナビ） ===== */
    .nav-wrap {
      position: relative;
      z-index: 10;
      padding: 20px 28px 0;
      display: flex;
      justify-content: center;
    }

    .nav-pill {
      background: rgba(255, 248, 236, 0.85);
      backdrop-filter: blur(10px);
      border-radius: 999px;
      padding: 12px 28px;
      display: flex;
      align-items: center;
      gap: 22px;
      box-shadow: 0 4px 20px rgba(60, 35, 15, 0.08);
      border: 1px solid var(--brown-100);
    }

    .nav-logo {
      font-family: 'Playfair Display', serif;
      font-size: 22px;
      font-weight: 900;
      color: var(--brown-800);
      letter-spacing: 0.5px;
    }
    .nav-logo span { color: var(--gold-500); }

    .nav-links {
      display: flex;
      gap: 18px;
      font-size: 13px;
      font-weight: 700;
    }
    .nav-links a { color: var(--brown-700); text-decoration: none; transition: color 0.2s; }
    .nav-links a:hover { color: var(--gold-600); }

    /* ===== ヒーローエリア ===== */
    .hero {
      position: relative;
      z-index: 5;
      padding: 80px 28px 60px;
      max-width: 1200px;
      margin: 0 auto;
      text-align: center;
    }

    /* ===== 固定背景のフクロウ（画面右下に常駐） ===== */
    .owl-fixed {
      position: fixed;
      bottom: 16px;
      right: 16px;
      width: auto;
      height: 30vh;          /* 画面高さの30% */
      max-height: 360px;
      pointer-events: none;  /* マウス操作の邪魔をしない */
      opacity: 0;            /* 初期は透明、登場アニメで表示 */
      z-index: 1;            /* コンテンツより奥 */
      filter: drop-shadow(0 8px 16px rgba(93, 58, 31, 0.25));
      animation:
        owlIn 1.2s cubic-bezier(0.22,1,0.36,1) 0.4s forwards,
        owlFloat 6s ease-in-out 1.6s infinite;
    }
    @keyframes owlIn {
      0%   { opacity: 0; transform: translate(40px, 20px) scale(0.9); }
      100% { opacity: 0.7; transform: translate(0, 0) scale(1); }
    }
    @keyframes owlFloat {
      0%, 100% { transform: translateY(0) rotate(-1deg); opacity: 0.7; }
      50%      { transform: translateY(-12px) rotate(1deg); opacity: 0.75; }
    }

    /* スマホ：邪魔にならないよう小さく */
    @media (max-width: 640px) {
      .owl-fixed {
        height: 22vh;
        max-height: 180px;
        bottom: 8px;
        right: 8px;
        opacity: 0.55;
      }
      @keyframes owlIn {
        0%   { opacity: 0; transform: translate(40px, 20px) scale(0.9); }
        100% { opacity: 0.55; transform: translate(0, 0) scale(1); }
      }
      @keyframes owlFloat {
        0%, 100% { transform: translateY(0) rotate(-1deg); opacity: 0.55; }
        50%      { transform: translateY(-8px) rotate(1deg); opacity: 0.6; }
      }
    }

    .hero-title-en {
      font-family: 'Playfair Display', serif;
      font-size: clamp(48px, 8vw, 96px);
      font-weight: 900;
      line-height: 1.05;
      letter-spacing: -1.5px;
      color: var(--brown-800);
      opacity: 0;
      transform: translateY(30px);
      animation: heroIn 0.9s cubic-bezier(0.22,1,0.36,1) 0.3s forwards;
    }
    .hero-title-en .accent { color: var(--gold-500); }

    .hero-sub-en {
      font-family: 'Playfair Display', serif;
      font-size: clamp(20px, 3vw, 32px);
      font-weight: 700;
      color: var(--brown-600);
      margin-top: 8px;
      letter-spacing: 0.5px;
      opacity: 0;
      transform: translateY(30px);
      animation: heroIn 0.9s cubic-bezier(0.22,1,0.36,1) 0.45s forwards;
    }

    .hero-tagline {
      margin-top: 24px;
      font-size: clamp(16px, 2.2vw, 20px);
      font-weight: 700;
      color: var(--brown-700);
      letter-spacing: 0.3px;
      opacity: 0;
      transform: translateY(20px);
      animation: heroIn 0.8s cubic-bezier(0.22,1,0.36,1) 0.6s forwards;
    }

    .hero-badge {
      display: inline-block;
      background: linear-gradient(135deg, var(--gold-500), var(--gold-600));
      color: #fff;
      padding: 6px 18px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      margin-top: 18px;
      letter-spacing: 0.5px;
      box-shadow: 0 4px 12px rgba(168, 127, 51, 0.3);
      opacity: 0;
      animation: heroIn 0.8s cubic-bezier(0.22,1,0.36,1) 0.75s forwards;
    }

    @keyframes heroIn {
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* SNSリンク */
    .social-row {
      display: flex;
      gap: 10px;
      justify-content: center;
      margin-top: 32px;
      flex-wrap: wrap;
      opacity: 0;
      animation: heroIn 0.8s cubic-bezier(0.22,1,0.36,1) 0.9s forwards;
    }

    .social-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 11px 20px;
      border-radius: 999px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 700;
      color: #fff;
      transition: transform 0.2s, box-shadow 0.2s;
      box-shadow: 0 4px 12px rgba(60, 35, 15, 0.15);
    }
    .social-btn:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(60, 35, 15, 0.25); }
    .social-btn svg { width: 16px; height: 16px; }

    .sb-x    { background: var(--brown-900); }
    .sb-yt   { background: #c8351a; }
    .sb-note { background: var(--gold-500); }

    /* ===== セクション共通 ===== */
    .section {
      position: relative;
      z-index: 5;
      max-width: 1200px;
      margin: 0 auto;
      padding: 60px 28px;
    }

    .section-head {
      margin-bottom: 36px;
      display: flex;
      align-items: baseline;
      gap: 16px;
      flex-wrap: wrap;
    }

    .section-title-en {
      font-family: 'Playfair Display', serif;
      font-size: clamp(32px, 5vw, 56px);
      font-weight: 900;
      color: var(--brown-800);
      letter-spacing: -0.5px;
      line-height: 1;
    }

    .section-title-jp {
      font-size: 14px;
      font-weight: 700;
      color: var(--gold-600);
      letter-spacing: 1px;
    }
    .section-title-jp::before {
      content: "●";
      margin-right: 8px;
      color: var(--gold-500);
    }

    .section-divider {
      height: 2px;
      background: linear-gradient(to right, var(--brown-700), transparent);
      margin-bottom: 36px;
    }

    /* ===== 検索＆タブカード ===== */
    .search-card {
      background: rgba(255, 252, 245, 0.85);
      backdrop-filter: blur(10px);
      border-radius: 24px;
      padding: 32px;
      box-shadow: var(--shadow);
      border: 1px solid var(--brown-100);
    }

    .search-box {
      width: 100%;
      padding: 14px 20px;
      font-size: 14px;
      border: 2px solid var(--brown-200);
      border-radius: 12px;
      font-family: 'Noto Sans JP', sans-serif;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
      background: #fff;
      color: var(--ink);
    }
    .search-box:focus {
      border-color: var(--gold-500);
      box-shadow: 0 0 0 4px rgba(196, 154, 74, 0.15);
    }

    .tabs {
      display: flex;
      gap: 4px;
      margin-top: 18px;
      border-bottom: 2px solid var(--brown-100);
      overflow-x: auto;
    }
    .tab {
      padding: 11px 16px;
      font-size: 13px;
      background: none;
      border: none;
      cursor: pointer;
      color: var(--muted);
      font-family: 'Noto Sans JP', sans-serif;
      font-weight: 700;
      white-space: nowrap;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      transition: color 0.2s, border-color 0.2s;
    }
    .tab.active {
      color: var(--brown-800);
      border-bottom-color: var(--gold-500);
    }
    .tab:hover { color: var(--brown-700); }

    .sp500-toolbar {
      margin-top: 14px;
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    .overview-btn {
      background: var(--brown-700);
      color: #fff;
      border: none;
      padding: 9px 16px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      font-family: 'Noto Sans JP', sans-serif;
      transition: background 0.2s;
    }
    .overview-btn:hover { background: var(--brown-800); }
    .overview-sort {
      padding: 8px 12px;
      border: 1px solid var(--brown-200);
      border-radius: 8px;
      font-size: 12px;
      font-family: 'Noto Sans JP', sans-serif;
      color: var(--ink);
      background: #fff;
      cursor: pointer;
    }

    .symbol-list {
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(82px, 1fr));
      gap: 6px;
      max-height: 280px;
      overflow-y: auto;
      padding: 4px;
    }
    .symbol-chip {
      padding: 9px 6px;
      background: var(--cream-100);
      border: 1px solid var(--brown-100);
      border-radius: 8px;
      cursor: pointer;
      text-align: center;
      font-size: 12px;
      font-weight: 700;
      color: var(--brown-800);
      transition: background 0.15s, transform 0.15s;
      user-select: none;
    }
    .symbol-chip:hover {
      background: var(--brown-700);
      color: #fff;
      transform: translateY(-1px);
    }
    .symbol-chip.active { background: var(--brown-700); color: #fff; }
    .symbol-chip.futures {
      background: linear-gradient(135deg, #f4dba0 0%, var(--gold-500) 100%);
      border-color: var(--gold-500);
      color: #fff;
      box-shadow: 0 2px 6px rgba(168, 127, 51, 0.3);
    }
    .symbol-chip.futures:hover {
      background: linear-gradient(135deg, var(--gold-500), var(--gold-600));
      color: #fff;
    }
    .symbol-chip.futures.active {
      background: linear-gradient(135deg, var(--gold-600), var(--brown-700));
      color: #fff;
    }

    .no-result {
      grid-column: 1 / -1;
      padding: 20px;
      text-align: center;
      color: var(--muted);
      font-size: 13px;
    }
    .count-info { margin-top: 10px; font-size: 11px; color: var(--muted); text-align: right; }

    /* 一気見グリッド */
    .overview-grid {
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 10px;
      max-height: 70vh;
      overflow-y: auto;
      padding: 6px;
      background: var(--cream-100);
      border-radius: 12px;
    }
    .thumb-card {
      background: #1a1208;
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.15s;
      border: 2px solid transparent;
    }
    .thumb-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(60, 35, 15, 0.25);
      border-color: var(--gold-500);
    }
    .thumb-card img { width: 100%; height: 64px; display: block; object-fit: cover; background: #131722; }
    .thumb-card .thumb-placeholder {
      width: 100%; height: 64px; display: flex; align-items: center; justify-content: center;
      color: #888; font-size: 10px; background: #2a2014;
    }
    .thumb-info {
      padding: 6px 8px; display: flex; justify-content: space-between;
      align-items: center; font-size: 11px;
    }
    .thumb-symbol { font-weight: 700; color: #fff; }
    .thumb-score { font-weight: 700; }
    .ts-blue { color: #00bfff; } .ts-green { color: #32cd32; }
    .ts-yellow { color: #ffd700; } .ts-red { color: #ff4444; } .ts-na { color: #777; }
    .overview-loading {
      padding: 30px; text-align: center; color: var(--muted);
      font-size: 13px; grid-column: 1 / -1;
    }

    /* ===== チャートエリア ===== */
    .chart-area {
      width: 100%;
      max-width: 1280px;
      margin: 0 auto 40px;
      display: none;
      gap: 16px;
      padding: 0 28px;
    }
    .chart-area.active { display: flex; flex-wrap: wrap; }

    .chart-main {
      flex: 1 1 600px;
      background: #131722;
      border-radius: 16px;
      overflow: hidden;
      min-width: 0;
      box-shadow: var(--shadow);
    }
    .info-panel {
      flex: 0 1 300px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-width: 240px;
    }
    .info-card {
      background: rgba(255, 252, 245, 0.95);
      border-radius: 16px;
      padding: 16px 18px;
      color: var(--ink);
      border: 1px solid var(--brown-100);
      box-shadow: 0 4px 16px rgba(60, 35, 15, 0.08);
    }
    .info-card-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--gold-600);
      margin-bottom: 12px;
      letter-spacing: 0.8px;
      text-transform: uppercase;
    }
    .info-card-title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 8px; }
    .info-card-title-row .info-card-title { margin-bottom: 0; }
    .compare-btn {
      background: var(--brown-700); color: #fff; border: none; padding: 6px 12px;
      border-radius: 999px; font-size: 11px; font-weight: 700; cursor: pointer;
      font-family: 'Noto Sans JP', sans-serif; white-space: nowrap; transition: background 0.2s;
    }
    .compare-btn:hover { background: var(--brown-800); }
    .compare-btn:disabled { background: #aaa; cursor: not-allowed; }
    .chart-header-actions { display: flex; align-items: center; gap: 8px; }
    .chart-action {
      background: rgba(196, 154, 74, 0.25); color: #fff;
      border: 1px solid rgba(196, 154, 74, 0.5); padding: 5px 10px;
      border-radius: 999px; font-size: 11px; font-weight: 700; cursor: pointer;
      font-family: 'Noto Sans JP', sans-serif; white-space: nowrap;
    }
    .chart-action:hover { background: rgba(196, 154, 74, 0.5); }
    .peer-color-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }

    .commentary-list { list-style: none; padding: 0; margin: 0; font-size: 13px; line-height: 1.7; }
    .commentary-list li { padding: 4px 0; color: var(--brown-800); }
    .peer-sector-name { font-size: 11px; color: var(--muted); margin-bottom: 8px; }
    .peer-list { list-style: none; padding: 0; margin: 0; font-size: 13px; }
    .peer-list li {
      display: flex; justify-content: space-between; padding: 6px 0;
      border-bottom: 1px solid var(--brown-100);
    }
    .peer-list li:last-child { border-bottom: none; }
    .peer-name { font-weight: 700; cursor: pointer; color: var(--brown-800); }
    .peer-name:hover { color: var(--gold-600); }
    .peer-change { font-weight: 700; }
    .peer-up { color: #2e8b3a; } .peer-down { color: #c4302b; } .peer-na { color: #999; }
    .info-empty { font-size: 12px; color: #999; padding: 8px 0; }

    .chart-header {
      padding: 14px 20px; color: white; font-size: 14px; font-weight: 700;
      background: #1e2230; display: flex; justify-content: space-between; align-items: center;
    }
    .chart-close {
      background: rgba(255,255,255,0.1); border: none; color: white;
      width: 28px; height: 28px; border-radius: 50%; cursor: pointer; font-size: 14px;
    }
    .chart-close:hover { background: rgba(255,255,255,0.25); }
    .chart-body { min-height: 200px; display: flex; align-items: center; justify-content: center; }
    .chart-body img { width: 100%; display: block; }
    .chart-loading { padding: 40px; color: #888; font-size: 13px; }
    .chart-error { padding: 30px; color: #ff6b6b; font-size: 13px; }

    /* ===== Note記事セクション ===== */
    .note-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 24px;
    }
    .note-card {
      background: #fff;
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(60, 35, 15, 0.1);
      border: 1px solid var(--brown-100);
      transition: transform 0.25s, box-shadow 0.25s;
      text-decoration: none;
      color: var(--ink);
      display: flex;
      flex-direction: column;
      opacity: 0;
      transform: translateY(20px);
    }
    .note-card.visible {
      opacity: 1; transform: translateY(0);
      transition: transform 0.6s cubic-bezier(0.22,1,0.36,1), opacity 0.6s;
    }
    .note-card:hover {
      transform: translateY(-6px);
      box-shadow: 0 16px 36px rgba(60, 35, 15, 0.18);
    }
    .note-card-thumb {
      width: 100%;
      aspect-ratio: 16 / 9;
      background: linear-gradient(135deg, var(--brown-100), var(--cream-200));
      display: flex; align-items: center; justify-content: center;
      color: var(--brown-300); font-size: 36px;
      overflow: hidden;
    }
    .note-card-thumb img { width: 100%; height: 100%; object-fit: cover; }
    .note-card-body { padding: 20px 22px 22px; flex: 1; display: flex; flex-direction: column; }
    .note-card-num {
      font-family: 'Playfair Display', serif;
      font-size: 14px; font-weight: 700; color: var(--gold-600); margin-bottom: 8px;
    }
    .note-card-title {
      font-size: 15px; font-weight: 700; line-height: 1.5; color: var(--brown-800);
      margin-bottom: 10px; display: -webkit-box;
      -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .note-card-preview {
      font-size: 12px; color: var(--muted); line-height: 1.6; margin-bottom: 16px;
      flex: 1; display: -webkit-box; -webkit-line-clamp: 3;
      -webkit-box-orient: vertical; overflow: hidden;
    }
    .note-card-action {
      display: inline-flex; align-items: center; gap: 6px;
      color: var(--gold-600); font-size: 12px; font-weight: 700;
    }
    .note-card-action svg { width: 14px; height: 14px; transition: transform 0.2s; }
    .note-card:hover .note-card-action svg { transform: translateX(4px); }
    .note-loading { text-align: center; padding: 40px; color: var(--muted); font-size: 13px; grid-column: 1 / -1; }

    /* ===== フッター ===== */
    .footer {
      margin-top: 60px;
      padding: 40px 28px 30px;
      background: var(--brown-800);
      color: var(--cream-100);
      text-align: center;
      font-size: 12px;
    }
    .footer-logo {
      font-family: 'Playfair Display', serif;
      font-size: 22px; font-weight: 900; margin-bottom: 8px;
    }
    .footer-logo span { color: var(--gold-400); }

    /* ===== スクロールリビール（汎用） ===== */
    .reveal { opacity: 0; transform: translateY(30px); transition: opacity 0.8s, transform 0.8s cubic-bezier(0.22,1,0.36,1); }
    .reveal.visible { opacity: 1; transform: translateY(0); }

    /* スマホ調整 */
    @media (max-width: 640px) {
      .nav-links { display: none; }
      .nav-pill { padding: 10px 18px; }
      .hero { padding: 50px 18px 40px; }
      .section { padding: 40px 18px; }
      .search-card { padding: 22px; }
      .chart-area { padding: 0 18px; }
    }

    /* ===== ローディング画面 ===== */
    .loader {
      position: fixed;
      inset: 0;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background:
        radial-gradient(ellipse at top left, var(--cream-100) 0%, transparent 50%),
        radial-gradient(ellipse at top right, #fbeacc 0%, transparent 50%),
        var(--cream-50);
      transition: opacity 0.8s ease, visibility 0.8s ease;
    }
    .loader.hidden { opacity: 0; visibility: hidden; pointer-events: none; }

    /* フクロウアイコン（丸枠あり） */
    .loader-owl {
      width: 140px;
      height: 140px;
      border-radius: 50%;
      object-fit: cover;
      border: 5px solid #fff;
      box-shadow:
        0 12px 32px rgba(93, 58, 31, 0.25),
        0 0 0 6px rgba(212, 168, 90, 0.35);
      animation: loaderOwlIn 0.7s cubic-bezier(0.22,1,0.36,1), loaderOwlPulse 1.8s ease-in-out 0.7s infinite;
    }
    @keyframes loaderOwlIn {
      0%   { opacity: 0; transform: translateY(20px) scale(0.85); }
      100% { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes loaderOwlPulse {
      0%, 100% { transform: scale(1); }
      50%      { transform: scale(1.06); }
    }

    /* ロゴ「トレンド研究所」 */
    .loader-logo {
      margin-top: 24px;
      font-family: 'Playfair Display', serif;
      font-size: clamp(28px, 5vw, 44px);
      font-weight: 900;
      color: var(--brown-800);
      letter-spacing: 1px;
      opacity: 0;
      animation: loaderTextIn 0.7s cubic-bezier(0.22,1,0.36,1) 0.3s forwards;
    }
    .loader-logo .accent { color: var(--gold-500); }
    @keyframes loaderTextIn {
      0%   { opacity: 0; transform: translateY(10px); }
      100% { opacity: 1; transform: translateY(0); }
    }

    .loader-sub {
      margin-top: 6px;
      font-family: 'Playfair Display', serif;
      font-size: clamp(11px, 1.6vw, 14px);
      font-weight: 700;
      color: var(--brown-600);
      letter-spacing: 2px;
      text-transform: uppercase;
      opacity: 0;
      animation: loaderTextIn 0.7s cubic-bezier(0.22,1,0.36,1) 0.5s forwards;
    }

    /* プログレスバー */
    .loader-progress {
      margin-top: 32px;
      width: 220px;
      height: 4px;
      background: var(--brown-100);
      border-radius: 2px;
      overflow: hidden;
      opacity: 0;
      animation: loaderTextIn 0.7s cubic-bezier(0.22,1,0.36,1) 0.7s forwards;
    }
    .loader-progress-bar {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--gold-500), var(--brown-700));
      border-radius: 2px;
      animation: loaderProgress 2s cubic-bezier(0.4, 0, 0.2, 1) 0.8s forwards;
    }
    @keyframes loaderProgress {
      0%   { width: 0%; }
      50%  { width: 60%; }
      100% { width: 100%; }
    }

  </style>
</head>
<body>

  <!-- ローディング画面（オープニング） -->
  <div class="loader" id="loader">
    <img class="loader-owl" alt="トレケン"
         src="data:image/jpeg;base64,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">
    <div class="loader-logo">トレンド<span class="accent">研究所</span></div>
    <div class="loader-sub">Trend Research Lab</div>
    <div class="loader-progress"><div class="loader-progress-bar"></div></div>
  </div>

  <!-- 浮遊する装飾（フクロウのテーマ：羽根と星） -->
  <div class="floaters" aria-hidden="true">
    <svg class="floater f1" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 4 L36 28 L60 32 L36 36 L32 60 L28 36 L4 32 L28 28 Z" fill="#d4a85a"/>
    </svg>
    <svg class="floater f2" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 6 C18 18, 14 30, 22 48 C26 56, 38 56, 42 48 C50 30, 46 18, 32 6 Z" fill="#8a5c3d"/>
      <path d="M32 14 L32 48" stroke="#704a2e" stroke-width="2"/>
    </svg>
    <svg class="floater f3" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="26" fill="none" stroke="#c49a4a" stroke-width="3"/>
      <circle cx="32" cy="32" r="14" fill="#d4a85a" opacity="0.6"/>
    </svg>
    <svg class="floater f4" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 4 L36 28 L60 32 L36 36 L32 60 L28 36 L4 32 L28 28 Z" fill="#704a2e"/>
    </svg>
  </div>

  <!-- ナビゲーション -->
  <div class="nav-wrap">
    <div class="nav-pill">
      <div class="nav-logo">Tore<span>ken</span></div>
      <div class="nav-links">
        <a href="#search">銘柄を探す</a>
        <a href="#notes">記事</a>
        <a href="https://x.com/Trade_CFD_FX" target="_blank" rel="noopener">X</a>
      </div>
    </div>
  </div>

  <!-- ヒーロー -->
  <section class="hero">
    <h1 class="hero-title-en">トレンド<span class="accent">研究所</span></h1>
    <div class="hero-sub-en">Candle Color Tells The Trend</div>
    <div class="hero-tagline">ろうそく足の色でトレンド把握 — トレケン式分析で次の一手を掴め！</div>
    <div class="hero-badge">投資判断のためのチャートデータベース</div>

    <div class="social-row">
      <a href="https://x.com/Trade_CFD_FX" target="_blank" rel="noopener" class="social-btn sb-x">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.743l7.733-8.835L1.254 2.25H8.08l4.256 5.622L18.244 2.25Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z"/></svg>
        @Trade_CFD_FX
      </a>
      <a href="https://www.youtube.com/@トレンド研究所" target="_blank" rel="noopener" class="social-btn sb-yt">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
        YouTube
      </a>
      <a href="https://note.com/natukb" target="_blank" rel="noopener" class="social-btn sb-note">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.5 0h-19C1.1 0 0 1.1 0 2.5v19C0 22.9 1.1 24 2.5 24h19c1.4 0 2.5-1.1 2.5-2.5v-19C24 1.1 22.9 0 21.5 0zM7 17.5c-.8 0-1.5-.7-1.5-1.5s.7-1.5 1.5-1.5 1.5.7 1.5 1.5-.7 1.5-1.5 1.5zm10-4H7v-2h10v2zm0-4H7V7.5h10V9.5z"/></svg>
        Note
      </a>
    </div>
  </section>

  <!-- 銘柄検索＆タブ -->
  <section class="section reveal" id="search">
    <div class="section-head">
      <div>
        <div class="section-title-jp">銘柄を探す</div>
        <div class="section-title-en">Search Stocks</div>
      </div>
    </div>
    <div class="section-divider"></div>

    <div class="search-card">
      <input type="text" class="search-box" id="searchBox" placeholder="🔍 全銘柄から検索（例: NVDA, AAPL, BTC）">

      <div class="tabs" id="tabs">
        <button class="tab active" data-group="G1">先物・米国株</button>
        <button class="tab" data-group="G2">セクター銘柄</button>
        <button class="tab" data-group="G3">暗号通貨</button>
        <button class="tab" data-group="SP500">S&amp;P 500</button>
      </div>

      <div class="sp500-toolbar" id="sp500Toolbar" style="display:none;">
        <button class="overview-btn" id="overviewBtn" onclick="toggleOverview()">📊 全銘柄を一気見</button>
        <select class="overview-sort" id="overviewSort" onchange="renderOverview()" style="display:none;">
          <option value="score_desc">スコア降順</option>
          <option value="score_asc">スコア昇順</option>
          <option value="symbol_asc">アルファベット順</option>
          <option value="sector">セクター順</option>
        </select>
      </div>

      <div class="symbol-list" id="symbolList"></div>
      <div class="overview-grid" id="overviewGrid" style="display:none;"></div>
      <div class="count-info" id="countInfo"></div>
    </div>
  </section>

  <!-- チャート表示エリア -->
  <div class="chart-area" id="chartArea">
    <div class="chart-main">
      <div class="chart-header">
        <span id="chartTitle">📈 ---</span>
        <div class="chart-header-actions">
          <button class="chart-action" id="restoreBtn" style="display:none" onclick="restoreSingleChart()">📈 元のチャートに戻す</button>
          <button class="chart-close" onclick="closeChart()" title="閉じる">✕</button>
        </div>
      </div>
      <div class="chart-body" id="chartBody"></div>
    </div>
    <div class="info-panel" id="infoPanel">
      <div class="info-card">
        <div class="info-card-title">📊 トレンド解説</div>
        <ul class="commentary-list" id="commentaryList">
          <li class="info-empty">チャートを選択すると表示されます</li>
        </ul>
      </div>
      <div class="info-card">
        <div class="info-card-title-row">
          <div class="info-card-title">🏭 同業他社の動き（1週間）</div>
          <button class="compare-btn" id="compareBtn" style="display:none" onclick="runCompare()">📊 同業比較</button>
        </div>
        <div class="peer-sector-name" id="peerSectorName"></div>
        <ul class="peer-list" id="peerList">
          <li class="info-empty">S&amp;P 500銘柄のみ対応</li>
        </ul>
      </div>
    </div>
  </div>

  <!-- Note記事セクション -->
  <section class="section reveal" id="notes">
    <div class="section-head">
      <div>
        <div class="section-title-jp">記事</div>
        <div class="section-title-en">Latest Articles</div>
      </div>
    </div>
    <div class="section-divider"></div>

    <div class="note-grid" id="noteGrid">
      <div class="note-loading">記事を読み込み中...</div>
    </div>
  </section>

  <!-- フッター -->
  <footer class="footer">
    <div class="footer-logo">Tore<span>ken</span></div>
    <div>© 2026 トレケン / トレンド研究所</div>
  </footer>

  <script>

    // ローディング画面（オープニング）の終了処理
    window.addEventListener('load', () => {
      setTimeout(() => {
        const loader = document.getElementById('loader');
        if (loader) loader.classList.add('hidden');
        // 完全に消えたあとDOM上から取り除く
        setTimeout(() => { if (loader) loader.remove(); }, 900);
      }, 2300);  // プログレスバーアニメーション(2.0s + 0.8sディレイ)に合わせて完了タイミング
    });

    const GROUPS = {
      G1: ['NQ1!','ES1!','TONX','FRSH','PAYC','GCTS','PXLW','FSLR','SIDU','VRNS','TRVG','TZOO','MAKO','HLP'],
      G2: ['KOS','GOOGL','INTC','NVDA','IONQ','FIGS','MU','RKLB','CRWV','LUNR','ATOM','KLXE','WTI','ESOA'],
      G3: ['BTC','ETH','SOL','XRP','ADA','DOGE','AVAX','LINK','MATIC','ATOMC'],
      SP500: [
'MMM','AOS','ABT','ABBV','ACN','ADBE','AMD','AES','AFL','A','APD','ABNB','AKAM','ALB','ARE',
        'ALGN','ALLE','LNT','ALL','GOOGL','GOOG','MO','AMZN','AMCR','AEE','AEP','AXP','AIG','AMT','AWK',
        'AMP','AME','AMGN','APH','ADI','AON','APA','APO','AAPL','AMAT','APP','APTV','ACGL','ADM','ARES',
        'ANET','AJG','AIZ','T','ATO','ADSK','ADP','AZO','AVB','AVY','AXON','BKR','BALL','BAC','BAX',
        'BDX','BRK-B','BBY','TECH','BIIB','BLK','BX','XYZ','BK','BA','BKNG','BSX','BMY','AVGO','BR',
        'BRO','BF-B','BLDR','BG','BXP','CHRW','CDNS','CPT','CPB','COF','CAH','CCL','CARR','CVNA','CASY',
        'CAT','CBOE','CBRE','CDW','COR','CNC','CNP','CF','CRL','SCHW','CHTR','CVX','CMG','CB','CHD',
        'CIEN','CI','CINF','CTAS','CSCO','C','CFG','CLX','CME','CMS','KO','CTSH','COHR','COIN','CL',
        'CMCSA','FIX','CAG','COP','ED','STZ','CEG','COO','CPRT','GLW','CPAY','CTVA','CSGP','COST','CTRA',
        'CRH','CRWD','CCI','CSX','CMI','CVS','DHR','DRI','DDOG','DVA','DECK','DE','DELL','DAL','DVN',
        'DXCM','FANG','DLR','DG','DLTR','D','DPZ','DASH','DOV','DOW','DHI','DTE','DUK','DD','ETN',
        'EBAY','SATS','ECL','EIX','EW','EA','ELV','EME','EMR','ETR','EOG','EPAM','EQT','EFX','EQIX',
        'EQR','ERIE','ESS','EL','EG','EVRG','ES','EXC','EXE','EXPE','EXPD','EXR','XOM','FFIV','FDS',
        'FICO','FAST','FRT','FDX','FIS','FITB','FSLR','FE','FISV','F','FTNT','FTV','FOXA','FOX','BEN',
        'FCX','GRMN','IT','GE','GEHC','GEV','GEN','GNRC','GD','GIS','GM','GPC','GILD','GPN','GL',
        'GDDY','GS','HAL','HIG','HAS','HCA','DOC','HSIC','HSY','HPE','HLT','HD','HON','HRL','HST',
        'HWM','HPQ','HUBB','HUM','HBAN','HII','IBM','IEX','IDXX','ITW','INCY','IR','PODD','INTC','IBKR',
        'ICE','IFF','IP','INTU','ISRG','IVZ','INVH','IQV','IRM','JBHT','JBL','JKHY','J','JNJ','JCI',
        'JPM','KVUE','KDP','KEY','KEYS','KMB','KIM','KMI','KKR','KLAC','KHC','KR','LHX','LH','LRCX',
        'LVS','LDOS','LEN','LII','LLY','LIN','LYV','LMT','L','LOW','LULU','LITE','LYB','MTB','MPC',
        'MAR','MRSH','MLM','MAS','MA','MKC','MCD','MCK','MDT','MRK','META','MET','MTD','MGM','MCHP',
        'MU','MSFT','MAA','MRNA','TAP','MDLZ','MPWR','MNST','MCO','MS','MOS','MSI','MSCI','NDAQ','NTAP',
        'NFLX','NEM','NWSA','NWS','NEE','NKE','NI','NDSN','NSC','NTRS','NOC','NCLH','NRG','NUE','NVDA',
        'NVR','NXPI','ORLY','OXY','ODFL','OMC','ON','OKE','ORCL','OTIS','PCAR','PKG','PLTR','PANW','PSKY',
        'PH','PAYX','PYPL','PNR','PEP','PFE','PCG','PM','PSX','PNW','PNC','POOL','PPG','PPL','PFG',
        'PG','PGR','PLD','PRU','PEG','PTC','PSA','PHM','PWR','QCOM','DGX','Q','RL','RJF','RTX',
        'O','REG','REGN','RF','RSG','RMD','RVTY','HOOD','ROK','ROL','ROP','ROST','RCL','SPGI','CRM',
        'SNDK','SBAC','SLB','STX','SRE','NOW','SHW','SPG','SWKS','SJM','SW','SNA','SOLV','SO','LUV',
        'SWK','SBUX','STT','STLD','STE','SYK','SMCI','SYF','SNPS','SYY','TMUS','TROW','TTWO','TPR','TRGP',
        'TGT','TEL','TDY','TER','TSLA','TXN','TPL','TXT','TMO','TJX','TKO','TTD','TSCO','TT','TDG',
        'TRV','TRMB','TFC','TYL','TSN','USB','UBER','UDR','ULTA','UNP','UAL','UPS','URI','UNH','UHS',
        'VLO','VTR','VLTO','VRSN','VRSK','VZ','VRTX','VRT','VTRS','VICI','V','VST','VMC','WRB','GWW',
        'WAB','WMT','DIS','WBD','WM','WAT','WEC','WFC','WELL','WST','WDC','WY','WSM','WMB','WTW',
        'WDAY','WYNN','XEL','XYL','YUM','ZBRA','ZBH','ZTS'
      ]
    };

    const FUTURES_SET = new Set(['NQ1!', 'ES1!']);

    let currentGroup = 'G1';
    let currentQuery = '';
    let activeSymbol = null;
    let lastPeerSymbols = [];
    let lastChartImage = null;
    let compareMode = false;

    function sortSymbols(arr) {
      const futures = [];
      const others = [];
      arr.forEach(s => {
        if (FUTURES_SET.has(s)) futures.push(s);
        else others.push(s);
      });
      futures.sort();
      others.sort((a, b) => a.localeCompare(b));
      return [...futures, ...others];
    }

    function renderSymbolList() {
      const list = document.getElementById('symbolList');
      const countInfo = document.getElementById('countInfo');
      const toolbar = document.getElementById('sp500Toolbar');
      const q = currentQuery.trim().toUpperCase();

      toolbar.style.display = (currentGroup === 'SP500') ? 'flex' : 'none';

      let displaySymbols, totalCount;
      if (q) {
        const allSymbols = [], seen = new Set();
        ['G1', 'G2', 'G3', 'SP500'].forEach(g => {
          (GROUPS[g] || []).forEach(s => {
            if (!seen.has(s)) { seen.add(s); allSymbols.push(s); }
          });
        });
        displaySymbols = sortSymbols(allSymbols.filter(s => s.toUpperCase().includes(q)));
        totalCount = allSymbols.length;
      } else {
        const symbols = GROUPS[currentGroup] || [];
        displaySymbols = sortSymbols(symbols);
        totalCount = symbols.length;
      }

      list.innerHTML = '';
      if (displaySymbols.length === 0) {
        const div = document.createElement('div');
        div.className = 'no-result';
        div.textContent = '該当する銘柄がありません';
        list.appendChild(div);
      } else {
        displaySymbols.forEach(sym => {
          const chip = document.createElement('div');
          let cls = 'symbol-chip';
          if (sym === activeSymbol) cls += ' active';
          if (FUTURES_SET.has(sym)) cls += ' futures';
          chip.className = cls;
          chip.textContent = sym;
          chip.onclick = () => loadChart(sym);
          list.appendChild(chip);
        });
      }
      countInfo.textContent = q
        ? `${displaySymbols.length} 件ヒット（全 ${totalCount} 銘柄から）`
        : `${displaySymbols.length} / ${totalCount} 銘柄`;
    }

    async function loadChart(sym) {
      activeSymbol = sym;
      compareMode = false;
      lastChartImage = null;
      lastPeerSymbols = [];
      renderSymbolList();

      const area = document.getElementById('chartArea');
      const title = document.getElementById('chartTitle');
      const body = document.getElementById('chartBody');
      const commentaryList = document.getElementById('commentaryList');
      const peerSectorName = document.getElementById('peerSectorName');
      const peerList = document.getElementById('peerList');
      const compareBtn = document.getElementById('compareBtn');
      const restoreBtn = document.getElementById('restoreBtn');

      area.classList.add('active');
      title.textContent = `📈 ${sym}`;
      body.innerHTML = '<div class="chart-loading">データ取得中...</div>';
      commentaryList.innerHTML = '<li class="info-empty">読み込み中...</li>';
      peerSectorName.textContent = '';
      peerList.innerHTML = '<li class="info-empty">読み込み中...</li>';
      compareBtn.style.display = 'none';
      restoreBtn.style.display = 'none';

      setTimeout(() => area.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);

      const chartPromise = fetch(`/chart/${encodeURIComponent(sym)}`)
        .then(r => r.json())
        .then(data => {
          if (data.image) {
            lastChartImage = data.image;
            body.innerHTML = `<img src="data:image/png;base64,${data.image}" alt="${sym}チャート">`;
          } else {
            body.innerHTML = `<div class="chart-error">⚠️ ${data.error || '取得失敗'}</div>`;
          }
        })
        .catch(() => { body.innerHTML = '<div class="chart-error">⚠️ サーバーに接続できません</div>'; });

      const infoPromise = fetch(`/info/${encodeURIComponent(sym)}`)
        .then(r => r.json())
        .then(data => {
          if (Array.isArray(data.commentary) && data.commentary.length > 0) {
            commentaryList.innerHTML = data.commentary.map(line => `<li>${escapeHtml(line)}</li>`).join('');
          } else {
            commentaryList.innerHTML = '<li class="info-empty">解説を生成できませんでした</li>';
          }
          if (data.peers && Array.isArray(data.peers.peers) && data.peers.peers.length > 0) {
            peerSectorName.textContent = data.peers.sector;
            peerList.innerHTML = data.peers.peers.map(p => {
              const ch = p.change;
              let cls = 'peer-na', label = '—';
              if (ch !== null && ch !== undefined) {
                cls = ch >= 0 ? 'peer-up' : 'peer-down';
                label = (ch >= 0 ? '+' : '') + ch.toFixed(2) + '%';
              }
              return `<li><span class="peer-name" onclick="loadChart('${p.symbol}')">${escapeHtml(p.symbol)}</span><span class="peer-change ${cls}">${label}</span></li>`;
            }).join('');
            lastPeerSymbols = [sym, ...data.peers.peers.map(p => p.symbol)];
            compareBtn.style.display = 'inline-block';
          } else {
            peerSectorName.textContent = '';
            peerList.innerHTML = '<li class="info-empty">同業他社情報なし（S&P 500外の銘柄）</li>';
            lastPeerSymbols = [];
          }
        })
        .catch(() => {
          commentaryList.innerHTML = '<li class="info-empty">情報を取得できません</li>';
          peerList.innerHTML = '<li class="info-empty">情報を取得できません</li>';
        });

      await Promise.all([chartPromise, infoPromise]);
    }

    async function runCompare() {
      if (!lastPeerSymbols || lastPeerSymbols.length < 2) return;
      const body = document.getElementById('chartBody');
      const title = document.getElementById('chartTitle');
      const peerList = document.getElementById('peerList');
      const restoreBtn = document.getElementById('restoreBtn');
      const compareBtn = document.getElementById('compareBtn');

      compareMode = true;
      title.textContent = `📊 ${activeSymbol} と同業他社の比較`;
      body.innerHTML = '<div class="chart-loading">比較チャートを作成中...</div>';
      compareBtn.disabled = true;

      try {
        const url = '/compare?symbols=' + encodeURIComponent(lastPeerSymbols.join(','));
        const res = await fetch(url);
        const data = await res.json();
        if (data.image) {
          body.innerHTML = `<img src="data:image/png;base64,${data.image}" alt="比較チャート">`;
          if (Array.isArray(data.legend)) {
            const colorMap = {};
            data.legend.forEach(it => { colorMap[it.symbol] = it.color; });
            peerList.querySelectorAll('li').forEach(li => {
              const nameEl = li.querySelector('.peer-name');
              if (!nameEl) return;
              const symName = nameEl.textContent.trim();
              if (colorMap[symName] && !li.querySelector('.peer-color-dot')) {
                const dot = document.createElement('span');
                dot.className = 'peer-color-dot';
                dot.style.background = colorMap[symName];
                nameEl.prepend(dot);
              }
            });
          }
          restoreBtn.style.display = 'inline-block';
        } else {
          body.innerHTML = `<div class="chart-error">⚠️ ${data.error || '比較失敗'}</div>`;
        }
      } catch (e) {
        body.innerHTML = '<div class="chart-error">⚠️ サーバーに接続できません</div>';
      } finally {
        compareBtn.disabled = false;
      }
    }

    function restoreSingleChart() {
      if (!lastChartImage || !activeSymbol) return;
      const body = document.getElementById('chartBody');
      const title = document.getElementById('chartTitle');
      const peerList = document.getElementById('peerList');
      const restoreBtn = document.getElementById('restoreBtn');

      compareMode = false;
      title.textContent = `📈 ${activeSymbol}`;
      body.innerHTML = `<img src="data:image/png;base64,${lastChartImage}" alt="${activeSymbol}チャート">`;
      peerList.querySelectorAll('.peer-color-dot').forEach(d => d.remove());
      restoreBtn.style.display = 'none';
    }

    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
    }

    function closeChart() {
      document.getElementById('chartArea').classList.remove('active');
      activeSymbol = null;
      renderSymbolList();
    }

    // ===== 一気見モード =====
    let overviewData = null;
    let overviewMode = false;

    async function toggleOverview() {
      const grid = document.getElementById('overviewGrid');
      const list = document.getElementById('symbolList');
      const countInfo = document.getElementById('countInfo');
      const sortSel = document.getElementById('overviewSort');
      const btn = document.getElementById('overviewBtn');

      if (overviewMode) {
        overviewMode = false;
        grid.style.display = 'none';
        list.style.display = '';
        countInfo.style.display = '';
        sortSel.style.display = 'none';
        btn.textContent = '📊 全銘柄を一気見';
        return;
      }
      overviewMode = true;
      list.style.display = 'none';
      countInfo.style.display = 'none';
      grid.style.display = 'grid';
      sortSel.style.display = 'inline-block';
      btn.textContent = '📋 リスト表示に戻す';
      grid.innerHTML = '<div class="overview-loading">データ取得中...</div>';

      if (!overviewData) {
        try {
          const res = await fetch('/sp500-all');
          overviewData = await res.json();
        } catch (e) {
          grid.innerHTML = '<div class="overview-loading">⚠️ サーバーに接続できません</div>';
          return;
        }
      }
      renderOverview();
    }

    function renderOverview() {
      if (!overviewData || !overviewData.items) return;
      const grid = document.getElementById('overviewGrid');
      const sort = document.getElementById('overviewSort').value;
      let items = overviewData.items.slice();
      if (sort === 'score_desc') items.sort((a, b) => (b.score ?? -Infinity) - (a.score ?? -Infinity));
      else if (sort === 'score_asc') items.sort((a, b) => (a.score ?? Infinity) - (b.score ?? Infinity));
      else if (sort === 'symbol_asc') items.sort((a, b) => a.symbol.localeCompare(b.symbol));
      else if (sort === 'sector') items.sort((a, b) => (a.sector || '').localeCompare(b.sector || '') || a.symbol.localeCompare(b.symbol));

      const html = items.map(it => {
        const sc = it.score;
        let scoreCls = 'ts-na', scoreLabel = '—';
        if (sc !== null && sc !== undefined) {
          if (sc >= 7) scoreCls = 'ts-blue';
          else if (sc > 0) scoreCls = 'ts-green';
          else if (sc <= -7) scoreCls = 'ts-yellow';
          else scoreCls = 'ts-red';
          scoreLabel = (sc >= 0 ? '+' : '') + sc.toFixed(1);
        }
        const thumbHtml = it.thumb
          ? `<img src="data:image/png;base64,${it.thumb}" alt="${escapeHtml(it.symbol)}">`
          : `<div class="thumb-placeholder">準備中</div>`;
        return `
          <div class="thumb-card" onclick="loadChart('${it.symbol}')">
            ${thumbHtml}
            <div class="thumb-info">
              <span class="thumb-symbol">${escapeHtml(it.symbol)}</span>
              <span class="thumb-score ${scoreCls}">${scoreLabel}</span>
            </div>
          </div>`;
      }).join('');

      grid.innerHTML = html;
      const cached = overviewData.cached_count || 0;
      const total = overviewData.total || 0;
      if (cached < total) {
        const info = document.createElement('div');
        info.className = 'overview-loading';
        info.style.fontSize = '12px';
        info.textContent = `${cached} / ${total} 銘柄のデータ準備済み（朝の自動更新後にすべて揃います）`;
        grid.prepend(info);
      }
    }

    // タブ切替
    document.querySelectorAll('.tab').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentGroup = btn.dataset.group;
        if (currentGroup !== 'SP500' && overviewMode) {
          overviewMode = false;
          document.getElementById('overviewGrid').style.display = 'none';
          document.getElementById('symbolList').style.display = '';
          document.getElementById('countInfo').style.display = '';
          document.getElementById('overviewSort').style.display = 'none';
          document.getElementById('overviewBtn').textContent = '📊 全銘柄を一気見';
        }
        renderSymbolList();
      };
    });

    // 検索ボックス
    document.getElementById('searchBox').addEventListener('input', e => {
      currentQuery = e.target.value;
      renderSymbolList();
    });

    // ===== Note記事の取得 =====
    async function loadNoteArticles() {
      const grid = document.getElementById('noteGrid');
      try {
        const res = await fetch('/note-articles');
        const data = await res.json();
        if (!Array.isArray(data.items) || data.items.length === 0) {
          grid.innerHTML = `
            <div class="note-loading">
              記事を取得できませんでした。
              <br><br>
              <a href="https://note.com/natukb" target="_blank" rel="noopener"
                 style="color: var(--gold-600); font-weight: 700;">
                Noteで直接見る →
              </a>
            </div>`;
          return;
        }
        grid.innerHTML = data.items.map((it, idx) => {
          const num = '(' + String(idx + 1).padStart(2, '0') + ')';
          const thumbHtml = it.thumb
            ? `<img src="${escapeHtml(it.thumb)}" alt="${escapeHtml(it.title)}">`
            : `<div style="font-size:48px;">📝</div>`;
          return `
            <a class="note-card" href="${escapeHtml(it.link)}" target="_blank" rel="noopener">
              <div class="note-card-thumb">${thumbHtml}</div>
              <div class="note-card-body">
                <div class="note-card-num">${num}</div>
                <div class="note-card-title">${escapeHtml(it.title)}</div>
                <div class="note-card-preview">${escapeHtml(it.preview || '')}</div>
                <span class="note-card-action">
                  記事を読む
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <line x1="5" y1="12" x2="19" y2="12"/>
                    <polyline points="12 5 19 12 12 19"/>
                  </svg>
                </span>
              </div>
            </a>`;
        }).join('');
        // 順番にフェードイン
        const cards = grid.querySelectorAll('.note-card');
        cards.forEach((card, idx) => {
          setTimeout(() => card.classList.add('visible'), idx * 150);
        });
      } catch (e) {
        grid.innerHTML = '<div class="note-loading">⚠️ 記事を取得できません</div>';
      }
    }

    // ===== スクロールリビール =====
    const reveals = document.querySelectorAll('.reveal');
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.1 });
    reveals.forEach(r => obs.observe(r));

    // 初期化
    renderSymbolList();
    loadNoteArticles();
  </script>
</body>
</html>
