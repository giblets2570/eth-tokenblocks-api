CREATE SCHEMA IF NOT EXISTS `ett` DEFAULT CHARACTER SET utf8 ;
USE `ett` ;

DROP TABLE IF EXISTS OrderBroker;
DROP TABLE IF EXISTS `Order`;
DROP TABLE IF EXISTS Token;
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Token (
    id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50),
    symbol VARCHAR(50),
    address VARCHAR(50),
    create_order_address VARCHAR(50),
    decimals INT(6),
    cutoff_time INT(6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE `Order` (
    id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    create_order_address VARCHAR(50),
    order_index INT(6) UNSIGNED,
    investor_id INT(6) UNSIGNED,
    token_id INT(6) UNSIGNED,
    state INT(6) UNSIGNED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (investor_id) REFERENCES User(id),
    FOREIGN KEY (token_id) REFERENCES Token(id)
);

CREATE TABLE OrderBroker (
    id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id INT(6) UNSIGNED,
    broker_id INT(6) UNSIGNED,
    amount VARCHAR(100),
    ik VARCHAR(200),
    ek VARCHAR(200),
    state INT(6) UNSIGNED,
    FOREIGN KEY (order_id) REFERENCES `Order`(id),
    FOREIGN KEY (broker_id) REFERENCES User(id)
);