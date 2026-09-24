BEGIN TRANSACTION;
CREATE TABLE admin (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        profile_image TEXT
    );
INSERT INTO "admin" VALUES(1,'praveen','waitingfordeath7815@gmail.com','$2b$12$5/5zVmJh/LpMbsvCSfKGGOatJ7DSpA794JFLcx4Un2/LGCl9qP3KC','jagan.jpg');
INSERT INTO "admin" VALUES(2,'bharat','praveenkumar78157815@gmail.com','$2b$12$q2Vu3QEEOk77dI.UHLW4EOwbZfJlseq.pDmQAGdDr1YS5xdtcIQq6',NULL);
CREATE TABLE cart (
        cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
    );
INSERT INTO "cart" VALUES(5,1,5,1);
CREATE TABLE order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT,
        quantity INTEGER,
        price REAL,
        address TEXT,
        FOREIGN KEY (order_id) REFERENCES orders (order_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    );
INSERT INTO "order_items" VALUES(1,1,1,'Product 1',1,19.0,NULL);
INSERT INTO "order_items" VALUES(2,2,6,'JBL Headset',1,45.0,NULL);
INSERT INTO "order_items" VALUES(3,3,4,'Infinix Note 50s',1,19999.0,NULL);
INSERT INTO "order_items" VALUES(4,5,6,'JBL Headset',1,45.0,'jfg');
INSERT INTO "order_items" VALUES(5,6,12,'Sony Home Theatre ',1,12999.0,'JNTU');
INSERT INTO "order_items" VALUES(6,7,1,'Product 1',1,19.0,'fghjk');
INSERT INTO "order_items" VALUES(7,8,4,'Infinix Note 50s',1,198.59,'AP');
INSERT INTO "order_items" VALUES(8,9,1,'Product 1',1,19.0,'Uppalapadu');
CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT,
        amount REAL,
        payment_status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        delivery_address TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    );
INSERT INTO "orders" VALUES(1,1,'order_TdMoB8KmO58I5v','pay_TdMoMAgk4aJXbI',19.0,'paid','2026-09-18 04:25:24',NULL);
INSERT INTO "orders" VALUES(2,1,'order_TdN36DgnIN2H4s','pay_TdN3JhJ9InU0se',45.0,'paid','2026-09-18 04:39:34',NULL);
INSERT INTO "orders" VALUES(3,1,'order_TdNL4Q0CAzEXuN','pay_TdNLMzgX7iJZMi',19999.0,'paid','2026-09-18 04:56:42',NULL);
INSERT INTO "orders" VALUES(5,1,'order_TdatBfb8eTvHpY','pay_TdatLSMpT09sv0',45.0,'paid','2026-09-18 18:11:52','jfg');
INSERT INTO "orders" VALUES(6,1,'order_TenUYTR3uVvkEx','pay_TenUmAUIFJM0az',12999.0,'paid','2026-09-21 19:10:38','JNTU');
INSERT INTO "orders" VALUES(7,1,'order_Teo8HMks2Yj0Nu','pay_Teo8THLnISiCtI',19.0,'paid','2026-09-21 19:48:16','fghjk');
INSERT INTO "orders" VALUES(8,1,'order_Tf6k0XJf7dyQoO','pay_Tf6kAw9Z6SIStc',198.59,'paid','2026-09-22 14:00:22','AP');
INSERT INTO "orders" VALUES(9,1,'order_TfRvPKfiXZGmdB','pay_TfRvgZRfv1nji4',19.0,'paid','2026-09-23 10:43:49','Uppalapadu');
CREATE TABLE products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        category TEXT,
        price REAL,
        image TEXT
    );
INSERT INTO "products" VALUES(1,'Product 1','silver chain with symbol of jesus','Accessories',19.0,'103410.jpg');
INSERT INTO "products" VALUES(4,'Infinix Note 50s','The Infinix Note 50s 5G+ is a mid-range smartphone featuring a 6.78-inch curved AMOLED display, a 144Hz refresh rate, and the MediaTek Dimensity 7300 Ultimate processor','Electronics',198.59,'mobile.jpg');
INSERT INTO "products" VALUES(5,'MacBook','The Apple MacBook Neo (512GB) is a 13-inch entry-level laptop built around the Apple A18 Pro chip, explicitly optimized for Apple Intelligence and AI workflows. The 512GB variant is highly recommended over the base model, as it uniquely includes an integrated Touch ID sensor and provides necessary breathing room for macOS system caches and media syncing','Electronics',549.41,'images.jpg');
INSERT INTO "products" VALUES(6,'JBL Headset','JBL offers a comprehensive lineup of audio gear tailored for everyday listening, office work, immersive gaming, and active use. These options balance powerful bass performance, comfortable form factors, and solid battery life across distinct price brackets.','Electronics',45.0,'images_1.jpg');
INSERT INTO "products" VALUES(7,'Black Shirt','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Clothes',699.0,'images_2.jpg');
INSERT INTO "products" VALUES(8,'Hoodie','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Clothes',499.0,'images_3.jpg');
INSERT INTO "products" VALUES(9,'Drinking Glass','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Home Appliances',1299.0,'images_8.jpg');
INSERT INTO "products" VALUES(10,'Sony Bravia AMOLED','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Home Appliances',828.53,'images_9.jpg');
INSERT INTO "products" VALUES(11,'Dining Table 6 Seater','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Home Appliances',27699.0,'images_11.jpg');
INSERT INTO "products" VALUES(12,'Sony Home Theatre ','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Home Appliances',12999.0,'images_10.jpg');
INSERT INTO "products" VALUES(13,'Tru Hair Wax','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Beauty',672.0,'images_7.jpg');
INSERT INTO "products" VALUES(14,'Men''s Face Kit','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Beauty',2789.0,'images_6.jpg');
INSERT INTO "products" VALUES(15,'Men''s Accessories Kit','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Fashion',1399.0,'images_5.jpg');
INSERT INTO "products" VALUES(16,'Shoe','The quick brown fox jumps over the lazy dog while the bright sun shines on the quiet meadow. Gentle breezes whisper through the tall green trees as distant birds sing a soft morning melody. Small blue waves gently touch the warm sandy shore under a clear and peaceful summer sky','Fashion',794.0,'images_4.jpg');
CREATE TABLE users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    );
INSERT INTO "users" VALUES(1,'lalita','lalithaande2007@gmail.com','$2b$12$vlBVliyp8UPjUBSf8MfDB.iP/SSLSH.Q.vYqE/1fRP.yHB/1pON4C');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('admin',2);
INSERT INTO "sqlite_sequence" VALUES('cart',5);
INSERT INTO "sqlite_sequence" VALUES('order_items',8);
INSERT INTO "sqlite_sequence" VALUES('orders',9);
INSERT INTO "sqlite_sequence" VALUES('products',16);
INSERT INTO "sqlite_sequence" VALUES('users',1);
COMMIT;
