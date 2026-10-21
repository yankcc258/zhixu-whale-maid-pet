# 服装位图生成记录

使用内置 `image_gen.imagegen`，未使用 API/CLI 替代。所有调用均要求真实透明背景。原 PSD 只用于提取只读位置指南与校验，57 个共用层由原 PSD 原样保留，不使用生成图替换。

以下为最终部件的提示词。生成部件按实际透明主体边界对齐到底稿坐标，去除极低透明度背景残留，分配至原有衣服槽位；完整立绘概念生成仅作设计检查，不作为交付的人物共用层。

## 衣身

输入 1：原 DressBase 层位置指南。输入 2：仓库睡衣参考。

Production Live2D clothing isolated layer. Image 1 is exact placement/silhouette EDIT TARGET on a 1086x1448 transparent canvas; image 2 is pajama DESIGN REFERENCE. Replace the navy maid dress with cream long button-front whale-pattern pajama tunic/nightshirt body. Preserve position and scale: garment ONLY lies at x300..780, y730..1185 on the 1086x1448 canvas, all other pixels transparent. Important only torso garment body, NO sleeves NO shoulder puffs, NO arms, no head or hair or skin. Draw complete hidden side edges from neck shoulder x435,y740 through armholes x420,y875 to flared hem x300..780,y1180. Neckline closed round/pajama small lapel collar. Cream fabric with pale blue whale and dot pattern, blue piping, little buttons in a central vertical row, smooth soft cel shading with folds at hem. Wide flared tunic fully fills original skirt area to y1185, simple hem blue piping, no lace, no apron or waistband. Match image 2 cream/blue palette and image1 dark navy smooth chibi outlines. No text. Genuine transparent background. Keep large empty transparent region above and below; don't center/enlarge isolated garment. Canvas ratio 3:4.

## 袖子初稿

输入 1：原袖子与袖口的透明位置指南。输入 2：仓库睡衣参考。

Production Live2D isolated sleeve pair layer. Image 1 exact POSITION/POSE edit target, image 2 cream/blue whale pajama design reference. Replace navy maid sleeves and ruffled cuffs with cream whale-print long pajama sleeves and simple wide straight blue-striped cuffs. Only TWO complete detached sleeves, nothing else: no torso, no hands, no skin, no head/hair. Full transparent 1086x1448 canvas. Keep exact placement, scale, angle image1: viewer-left sleeve shoulder x385,y785 extends down outward to cuff x275,y983; viewer-right shoulder x687,y785 to cuff x773,y983. Each sleeve must be complete all the way into shoulder socket even hidden parts: rounded shoulder x350..440,y755..850 and x620..725,y755..850. Cuff follows original diagonal wrist angle and ends at original wrist boundary. Smooth modestly loose sleeves, pale blue whale silhouettes and dots, cream fabric, pale blue cuffs with cream stripe, dark navy clean outlines and softly cel-shaded folds. No ruffles, no navy old fabric, no holes or ragged stray pixels. Match reference style. Huge transparent region above y750 and below y1040 preserved; do NOT center or enlarge. Both arms angled outward down just as target image.

## 袖子肩端补齐（最终稿）

输入：上一轮生成的袖子初稿。

Precise Live2D cutout repair. Keep both cream whale-print pajama sleeves, cuffs, palette, linework, size, placement, arm angle, canvas and every existing visible detail unchanged. Repair ONLY their shoulder ends. Currently each shoulder top has a concave black transparent missing bite where it touched the torso. Fill those bites completely with matching cream cloth and pale blue whale pattern, so EACH sleeve has a smooth rounded CONVEX closed shoulder cap extending into the hidden shoulder socket. Left sleeve top should be a complete rounded dome at x350..460 y755..875, right sleeve dome x620..735 y755..875 (coordinates for 1086x1448 canvas). Think of each as a detached long sleeve removed from a shirt, with full closed rounded upper arm, no cutouts, no notch, no holes. Keep the pair separate and disconnected, no shirt torso bridging them. Do not add hands, skin, hair, text or anything else. Do not change cuffs or forearms. Genuine transparent background.

## 裤腿与拖鞋

输入 1：原腿、鞋位置指南。输入 2：仓库睡衣参考。

Production Live2D isolated pajama trouser legs and slippers. Image1 exact POSITION and size edit target. Image2 cream/blue whale-print pajama design reference. Edit only the two stocking legs and shoes to cream whale-print loose pajama trouser legs with soft pale blue closed house slippers. No visible skin. NO other body parts or garments. Match exact 1086x1448 canvas placement and scale: left leg x375..505 y1115..1345, left slipper x350..485 y1305..1418; right leg x570..705 y1115..1345, right slipper x595..730 y1305..1418. Legs both stand like target, slight outward hip/knee angle, extend trousers upwards hidden under tunic to y1090. No stripes from stockings or old navy shoe straps. Cream cloth soft folds and scattered little powder blue whales, simple blue piping at trouser cuffs, soft blue slippers with small whale emblem. Dark navy clean chibi outlines and soft cel shading. All background genuine transparency. Keep enormous empty transparent region above y1090, don't center or enlarge the legs. No text, no skin/hands/hair.

## 睡帽初稿

输入 1：原 Headband 层位置指南。输入 2：原默认立绘。输入 3：仓库睡衣参考。

Production Live2D isolated nightcap head accessory layer. Image1 edit target is original headband accessory exact placement guide, image2 the full character for scale/position ONLY, image3 pajama nightcap design reference. Replace maid headband by cream and pale blue whale-print floppy sleeping cap with soft pompom at viewer upper right. ONLY isolated cap, NO hair, no face, no skin or other character parts, no eyebrows, no loose strands. Full 1086x1448 transparent canvas, cap lies above the existing hair and follows headband arch: broad cream band from x250,y390 arching to x520,y150 down to x855,y445. Simple pale blue trim at band edges. Soft pointed fabric crown behind it occupies x420..865 y110..300, pointed tip droops to small pompom x900,y280. Preserve original character ahoge open area at top left. Smooth clean dark navy outlines, soft cel shading, pale blue whale/dots prints, match reference3 colors and style. Must look like a soft sleep cap, not frilled maid band. Genuine transparent background all except cap. No text. Huge empty area below y470 and original scale retained, do not center/enlarge cap. Remove all skin triangles from guide, all isolated stray old pixels.

## 睡帽弧度修正（最终稿）

输入 1：原 Headband 层位置指南。输入 2：睡帽初稿。输入 3：原默认立绘。

Precise production Live2D accessory redraw. Image1 is the required original headband SHAPE/POSITION. Image2 is the desired cream pale blue whale-print nightcap DESIGN. Image3 original character only for scale. Draw ONLY isolated nightcap no character. Redraw image2 with its brim following the entire arch shape of image1 much more closely: brim is a broad symmetrical upside-down U arch, apex at (540,150) upper edge and (540,225) lower edge; LEFT tip extends down to (245,430) and RIGHT tip to (860,455). Left half must reach as far down as original image1 band so the underlying cut hair is covered. Brim arch like image1 not a diagonal tilted strip. Add soft whale-pattern cap crown above the arch (x420..830 y130..260), gently drooping point and pompom on right x880..915 y385..460. Preserve cream whale-pattern fabric, blue piping, smooth dark navy outline, soft cel-shading from image2. No frills, no maid lace, no hair, no face, NO skin triangles from guide. Exact 1086x1448 transparent canvas placement, empty everywhere below y480. Do not center or enlarge. Transparent background.
