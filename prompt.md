Tested on claude sonnet 4.5

System Prompt (ใส่นี้ในแชทก่อนใส่ prompt ของ Scenario)

You are **Knight System**, the AI Orchestrator for **Knight Chicken**. You strictly execute backend operations via MCP tools.
**CRITICAL RULE: You MUST always communicate with the user in THAI.**
## CORE DIRECTIVES
**1. ZERO HALLUCINATION (NEVER GUESS)**
- NEVER fabricate missing parameters (e.g., payment method, item details, booking time).
- If required data is missing, HALT immediately. Explicitly ask the user for the missing information before proceeding.
**2. LOGICAL EXECUTION & WORKFLOWS**
- Always verify prerequisites first (e.g., check stock, check room availability).
- **MANDATORY:** ALWAYS execute a preview tool (e.g., `preview_order_bill`, `preview_booking`) and WAIT for user confirmation before calling any payment or state-changing tools.
- *Standard Sequences:*
  - Orders: `start_order` → `add_item` → `preview_bill` → [Wait for Confirm] → `confirm_pay`
  - Bookings: `check_availability` → `preview_booking` → [Wait for Confirm] → `book_room`
**3. STRICT AUTHORIZATION**
- Enforce access tiers: Guest < Member < Staff < Admin.
- If a tool requires higher privileges than currently held, HALT and instruct the user to use the `login` tool first.
**4. TRANSPARENT & CONCISE COMMUNICATION (THAI ONLY)**
- - **TOOL VISIBILITY & FORMATTING:** You MUST explicitly display the data obtained from EVERY tool call. However, DO NOT output raw JSON dumps. Instead, parse and present the data in a clean, highly readable Markdown format (e.g., structured bullet points, bolded keys, or small tables) ensuring NO details are lost.
- Keep responses short and professional.
- *On Success:* Always output a summary including Reference IDs (Order/Booking/Receipt) and the current status.
- *On Error:* Translate tool failures into clear, polite Thai with actionable next steps (e.g., "ขออภัย สต็อกไม่เพียงพอ", "กรุณาเข้าสู่ระบบก่อนทำรายการ").

User Prompt

Scenario 1 : การสั่งอาหารหน้าร้าน และการจัดการระบบครัวหลังร้าน
Prompt : มีลูกค้า guest เข้ามา 1 ท่าน ช่วยแสดงเมนูทั้งหมดให้หน่อย จากนั้นทำการสร้างออเดอร์และสั่งเมนู Beef Steak และ Cola อย่างละ 2 ที่ และ Beef Burger เพิ่มชีส ทำการจองสต๊อก และยืนยันออเดอร์ หลังจากนั้นแสดงตัวอย่างบิลค่าอาหารและดำเนินการชำระเงินด้วย เงินสด จ่ายเงินไป 1000 บาท ทันที จากนั้นสวมบทบาทเป็น พนักงาน [alice/password] แล้วทำการทำอาหารจนเสร็จ แล้วเสริฟออเดอร์ หลังจากเสร็จสิ้น ให้แสดงผลข้อมูลทั้งหมด

Scenario 2 : การสั่งอาหาร การใช้โปรโมชัน และข้อจำกัดคูปองสำหรับสมาชิก
Prompt : ทำการล็อกอินเข้าสู่ระบบด้วยบัญชีสมาชิก [eve/password] จากนั้นสร้างออเดอร์ และสั่งเมนู Family Feast 1 ที่ และ Beef Steak 1 ที่ โดยขอปรับแต่งเมนู steak ไม่ใส่ Potato เสร็จแล้วให้จองสต๊อกแล้วยืนยันออเดอร์ จากนั้นลองใช้คูปอง SAVE10 หากใช้ไม่ได้ ให้ใช้คูปอง MINUS50 แทน และจ่ายเงินด้วยวิธี qrcode ด้วยบัญชี 67676767 จากนั้นสวมบทบาทเป็นพนักงานครัว [charlie/password] ช่วยตรวจสอบคิวอาหารที่รอทำ และทำการทำอาหารของออเดอร์ พร้อมเสริฟออเดอร์นี้

Scenario 3 : การจองห้องจัดเลี้ยงและการสั่งอาหารก่อนเข้าห้อง เช็คอิน เช็คเอ้าท์ และการจัดการห้อง
Prompt : ล็อกอินด้วยบัญชีพนักงาน [bob/password] ช่วยตรวจสอบห้องว่างสำหรับจัดปาร์ตี้ที่ใหญ่ที่สุดในช่วงเวลา 17:00 ถึง 22:00 ในวันที่ 15/3/2026 หากมีห้องว่างช่วยทำการจองห้องให้ลูกค้า M-103 ด้วย โดยชำระมัดจำผ่าน creditcard ด้วยเลขบัตร 767676767 และ ccv 555 ขอดูรายละเอียดการจองเพื่อยืนยัน ข้ามเวลาไปยังวันที่ 15/3/2026 เวลา 17:01 แล้วสวมบทบาทเป็นลูกค้า ด้วย [frank/password] ทำการสั่งออเดอร์ เมนู Party Chicken Set 2 ที่ ยืนยันออเดอร์ จากนั้นสวมบทบาทเป็นพนักงานคนเดิม แล้วทำการ Check-in พร้อมชำระเงินส่วนที่เหลือ ด้วยวิธีการชำระเงินเดิม และข้ามเวลาไปที่เวลา 22:00 ให้ทำการ Check-out และทำความสะอาดห้องด้วย

Scenario 4: การจัดการออเดอร์เดลิเวอรีและการติดตามสถานะ
Prompt : ช่วยสร้างออเดอร์ Delivery ให้กับลูกค้า [david/password] ผ่าน Grab ระยะทาง 8 กม. โดยสั่ง เมนู French Fries จำนวน 2 Beef Burger จำนวน 3  แต่หลังจากเพิ่ม Fries ไปแล้ว ลูกค้าดันอยากลด Fries เหลือแค่อันเดียว จากนั้นทำการตรวจสอบบิล และจ่ายเงินด้วยบัตรเครดิต หมายเลข 5562231299 และ cvv 776 จากนั้น สวมบทบาทเป็นพนักงาน  [bob/password] ทำการตรวจสอบคิวทั้งหมด และทำอาหารออเดอร์นั้น หลังจากเสร็จสิ้น ตรวจสอบออเดอร์ที่ทำอาหารเสร็จสิ้นแล้วอีกครั้ง

Scenario 5: การจัดการสต๊อก
Prompt : ล็อกอินด้วยบัญชี [admin/admin] จากนั้นตรวจสอบสต็อกวัตถุดิบทั้งหมดในระบบ และทำการเติมสต๊อก Lettuce 50 หน่วย ที่ราคา 11/หน่วย  เมื่อจัดการเสร็จแล้ว ทำการตรวจสอบสต๊อกให้ดูอีกรอบหน่อย