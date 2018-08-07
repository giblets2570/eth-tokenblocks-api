use gift;

DROP TABLE IF EXISTS User;

CREATE TABLE User (
	id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
	ik VARCHAR(300),
	spk VARCHAR(300),
	signature VARCHAR(300),
	nonce VARCHAR(50),
	address VARCHAR(50),
	role VARCHAR(50),
	name VARCHAR(50),
	password VARCHAR(300),
	truelayer_account_id VARCHAR(50),
	truelayer_access_token VARCHAR(1500),
	truelayer_refresh_token VARCHAR(100),
	created_at TIMESTAMP
);