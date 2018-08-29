CREATE SCHEMA IF NOT EXISTS `ett` DEFAULT CHARACTER SET utf8 ;
USE `ett`;

DROP TABLE IF EXISTS TradeOrder;
DROP TABLE IF EXISTS Trade;
DROP TABLE IF EXISTS OrderBroker;
DROP TABLE IF EXISTS `Order`;
DROP TABLE IF EXISTS TokenHolding;
DROP TABLE IF EXISTS TokenBalance;
DROP TABLE IF EXISTS Token;
DROP TABLE IF EXISTS User;

CREATE TABLE User (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ik VARCHAR(300),
    spk VARCHAR(300),
    signature VARCHAR(300),
    nonce VARCHAR(50),
    address VARCHAR(50),
    role VARCHAR(50),
    name VARCHAR(50),
    password VARCHAR(300),
    truelayerAccountId VARCHAR(50),
    truelayerAccessToken VARCHAR(1500),
    truelayerRefreshToken VARCHAR(100),
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Token (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    createOrderAddress VARCHAR(50),
    address VARCHAR(50),
    cutoffTime INT,
    symbol VARCHAR(50),
    name VARCHAR(50),
    decimals INT,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE TokenBalance (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tokenId INT UNSIGNED,
    investorId INT UNSIGNED,
    balance BIGINT,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tokenId) REFERENCES Token(id),
    FOREIGN KEY (investorId) REFERENCES User(id)
);

CREATE TABLE TokenHolding (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(50),
    stock INT,
    tokenId INT UNSIGNED,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tokenId) REFERENCES Token(id)
);

CREATE TABLE `Order` (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    investorId INT UNSIGNED,
    brokerId INT UNSIGNED,
    tokenId INT UNSIGNED,
    ik VARCHAR(200),
    ek VARCHAR(200),
    nominalAmount VARCHAR(100),
    price VARCHAR(100),
    executionDate INT UNSIGNED,
    expirationTimestampInSec INT UNSIGNED,
    salt INT UNSIGNED,
    state INT UNSIGNED, -- 0 == initialize, 1 == created, 2 == confirmed, 3 == investor cancel, 4 == broker cancel
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tokenId) REFERENCES Token(id),
    FOREIGN KEY (brokerId) REFERENCES User(id),
    FOREIGN KEY (investorId) REFERENCES User(id)
);

CREATE TABLE OrderBroker (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    brokerId INT UNSIGNED,
    ik VARCHAR(200),
    ek VARCHAR(200),
    nominalAmount VARCHAR(100),
    price VARCHAR(100),
    orderId INT UNSIGNED,
    state INT, -- 0 == initialize, 1 == chosen, 2 == disguarded
    FOREIGN KEY (brokerId) REFERENCES User(id),
    FOREIGN KEY (orderId) REFERENCES `Order`(id)
);

CREATE TABLE Trade (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    brokerId INT UNSIGNED,
    signature VARCHAR(300),
    verified BOOLEAN,
    FOREIGN KEY (brokerId) REFERENCES User(id)
);

CREATE TABLE TradeOrder (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    orderId INT UNSIGNED,
    tradeId INT UNSIGNED,
    FOREIGN KEY (orderId) REFERENCES `Order`(id),
    FOREIGN KEY (tradeId) REFERENCES Trade(id)
);


