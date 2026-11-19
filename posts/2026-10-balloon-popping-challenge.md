---
title: 用模擬火箭打氣球：Balloon Popping Challenge 2026 紀錄
date: 2026-10-11
lang: zh
tags: [強化學習, PPO, SLURM, 競賽]
summary: TASTI 2026 的火箭 GNC 軟體競賽，80 多隊、7 國參賽，我一個人打進決賽拿到第 5 名：在實驗室叢集上用 PPO 訓練一個打氣球的 agent，以及一路上做過的決定。
---

*English summary:* For the Balloon Popping Challenge at TASTI 2026 I trained an agent that flies a simulated 6-DoF rocket through 100 rising balloons. Over about two and a half weeks I ran reinforcement learning (PPO) on my lab's SLURM cluster, working with an AI pair-programmer that wrote much of the code and kept a decision log. This post covers what I decided along the way: a third on-policy data round the assistant thought was pointless (it was the turning point), how the shared cluster was used, and how seeds were handled for the qualification round on 10 October. Result: I entered solo, qualified as one of five finalists for the on-site final at TASTI (8 November, ICC Tainan), and finished 5th out of 80+ teams from 7 countries.

## 題目

這是國家太空中心（TASA）主辦、2026 年台灣太空國際年會（TASTI 2026，Taiwan International Assembly of Space Science, Technology, and Industry）上的「Balloon Popping Challenge 火箭導控軟體競賽」，比的是火箭導引、導航與控制（GNC）軟體，協辦並開源提供模擬環境的是國立陽明交通大學 ARRC 前瞻火箭研究中心。這屆共 80 多隊、來自 7 個國家，我是一個人參賽。

用兩三句話說：參賽者寫一個 Python 程式，控制一枚在物理模擬裡飛行的火箭（六自由度，也就是位置和姿態都要管），去撞破陸續從地面升空、隨風飄移的 100 顆氣球，只能發射一次，打越多越好。燃料大約只夠燒 30 秒，總共約 400 m/s 的 Δv（能改變的速度），光是對抗重力待在空中就要用掉約 294 m/s。最反直覺的是：油門關小不會省油，燃料消耗只跟時間有關，關小油門只是把推力丟掉。

時程很趕：9/23 才動手，leaderboard 9/26 00:05 截止（scenario 1、可以自己挑 seed，前 10 名晉級）；9/26 公布資格賽用的 scenario 4，多了感測器雜訊、致動器延遲和陣風；10/10 線上資格賽，主辦方當場抽 seed，跑兩次加總，取 3 到 5 隊進決賽；11/8 在台南 ICC 的 TASTI 會場現場決賽。

## 從監督式學習到強化學習

起點是手寫的 GNC agent，保留集平均 4.62 顆。第一個想法是用監督式學習學一個「這一段飛不飛得到那顆氣球」的模型，取代 beam search 裡的解析公式。

| 輪次 | 資料 | 平均顆數 |
|---|---|---|
| 1 | 5.9 萬筆，用公式版 Beam 蒐集 | 1.06 |
| 2 | 加上放寬時間的探索 | 1.26 |
| 3 | 改用學習版 Beam 自己蒐集（on-policy） | **4.67** |

第 2 輪之後，AI 助手判斷再跑一輪沒有用。我還是要它跑第 3 輪，結果分數一口氣追上手寫 GNC，它在紀錄裡寫下「我的判斷是錯的」。這是整個專案的轉折：資料要從目前的 policy 自己蒐集。

但 4 到 5 顆離前段班還很遠。分析公開的 replay 後發現，前段班大約每 2 秒打一顆，相對氣球群的速度是我的兩三倍；單純把參數調快，分數反而崩到 2 顆左右。所以改走強化學習：PPO 的 policy 選下一顆目標和速度檔，實際飛行仍交給 GNC 的導引律，再用 Beam 的決策做行為複製當起點，一開始就有 6 顆。

## 叢集

模擬器用 CPU 積分，GPU 加速不了，瓶頸是 CPU 數量。我用的是自己建的那套實驗室 SLURM 叢集（11 台節點）。因為實驗室其他人也在用，我一開始就要求不要影響別人：用 array job 限制同時執行的數量；後來大部分 worker 改用可被搶占的低優先權 QoS，別人一送工作，我們就讓出節點，再由看守腳本等節點空出來補回去。只有 learner 這種被砍掉會中斷訓練的工作才用一般優先權。

有兩次我推翻了助手的建議：它認為小節點拿去挑 seed 比較划算，我要它做跨節點訓練，吞吐量大約變兩倍；它認為非同步收集要花半天、不划算，我還是要做，最後 300 多個 worker 一起餵 GPU 上的 learner。

## Leaderboard

截止前三小時，我決定把資源全部改成「找好打的 seed，再在上面微調」，最後以 13 顆的成績晉級前十。

## 資格賽準備

scenario 4 不能挑 seed，比的是一般能力。最後一輪挑選拿 1024 個沒用過的 seed，比較交件檔和五個較新的 checkpoint，規則是至少好 2 個標準誤才換；沒有一個達到，交件檔不換，它在沒見過的 seed 上平均每局約 10.7 顆。

seed 方面，我把過去所有 log 重建一遍，整理出 1,109,176 個用過的 seed 交給主辦方。比賽用的腳本會先查抽到的 seed 有沒有用過，再改設定檔、跑官方的評估程式，最後把這個 seed 記進紀錄。比賽在我自己的電腦上跑，邊跑邊分享畫面。

## 結果

資格賽晉級，成為 5 支決賽隊伍之一；11/8 到台南 ICC 的 TASTI 2026 會場做技術簡報和現場 demo，最後是第 5 名（共 80 多隊、7 個國家）。

## 和 AI 一起做

老實說，這個專案大部分的程式是 AI 助手 Claude 寫的，那份 185 節的決策紀錄也是它寫的，裡面的「我」是它，「使用者」是我。我負責的是方向和取捨：要不要多跑一輪、資源怎麼分、什麼時候停、怎麼回覆主辦方。它很會把事情做完、把數字算清楚，但判斷不一定對；我的直覺也不一定對，例如我猜晚點起飛比較好，量出來 10 到 40 秒幾乎沒差。這次最有用的，是那份逐條記下「當時知道什麼、決定什麼、後來怎樣」的紀錄。
