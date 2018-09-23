CREATE SCHEMA IF NOT EXISTS `ett` DEFAULT CHARACTER SET utf8;
USE `ett`;

DROP TABLE IF EXISTS OrderTrade;
DROP TABLE IF EXISTS TradeBroker;
DROP TABLE IF EXISTS Trade;
DROP TABLE IF EXISTS OrderHolding;
DROP TABLE IF EXISTS `Order`;
DROP TABLE IF EXISTS TokenHolding;
DROP TABLE IF EXISTS TokenHoldings;
DROP TABLE IF EXISTS TokenBalance;
DROP TABLE IF EXISTS SecurityTimestamp;
DROP TABLE IF EXISTS Security;
DROP TABLE IF EXISTS NavTimestamp;
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
    email VARCHAR(300),
    truelayerAccountId VARCHAR(50),
    truelayerAccessToken VARCHAR(1500),
    truelayerRefreshToken VARCHAR(100),
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Token (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    address VARCHAR(50),
    cutoffTime INT UNSIGNED,
    symbol VARCHAR(50),
    name VARCHAR(50),
    fee INT UNSIGNED,
    ownerId INT UNSIGNED,
    decimals SMALLINT UNSIGNED,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ownerId) REFERENCES User(id)
);

CREATE TABLE NavTimestamp (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tokenId INT UNSIGNED,
    value INT UNSIGNED,
    executionDate DATE, 
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tokenId) REFERENCES Token(id)
);  

CREATE TABLE Security (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50),
    name VARCHAR(50),
    currency VARCHAR(50),
    country VARCHAR(50),
    sector VARCHAR(50),
    class VARCHAR(50),
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE SecurityTimestamp (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    securityId INT UNSIGNED,
    price INT UNSIGNED,
    state INT UNSIGNED, 
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (securityId) REFERENCES Security(id)
);  

CREATE TABLE TokenBalance (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tokenId INT UNSIGNED,
    userId INT UNSIGNED,
    balance BIGINT UNSIGNED DEFAULT 0,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tokenId) REFERENCES Token(id),
    FOREIGN KEY (userId) REFERENCES User(id)
);

CREATE TABLE TokenHoldings (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tokenId INT UNSIGNED,
    executionDate DATE,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tokenId) REFERENCES Token(id)
);

CREATE TABLE TokenHolding (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    securityId INT UNSIGNED,
    securityAmount INT UNSIGNED,
    tokenHoldingsId INT UNSIGNED,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tokenHoldingsId) REFERENCES TokenHoldings(id),
    FOREIGN KEY (securityId) REFERENCES Security(id)
);

CREATE TABLE Trade (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    investorId INT UNSIGNED,
    brokerId INT UNSIGNED,
    tokenId INT UNSIGNED,
    ik VARCHAR(200),
    ek VARCHAR(200),
    nominalAmount VARCHAR(100),
    price VARCHAR(100),
    executionDate DATE,
    expirationTimestampInSec BIGINT UNSIGNED,
    salt INT UNSIGNED,
    state INT UNSIGNED DEFAULT 0, -- 0 == created, 1 == confirmed, 2 == verified, 3 == investor cancel, 4 == broker cancel
    signature VARCHAR(300),
    hash VARCHAR(200),
    sk VARCHAR(200),
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tokenId) REFERENCES Token(id),
    FOREIGN KEY (brokerId) REFERENCES User(id),
    FOREIGN KEY (investorId) REFERENCES User(id)
);

CREATE TABLE TradeBroker (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    brokerId INT UNSIGNED,
    ik VARCHAR(200),
    ek VARCHAR(200),
    nominalAmount VARCHAR(100),
    price VARCHAR(100),
    tradeId INT UNSIGNED,
    state INT, -- 0 == initialize, 1 == chosen, 2 == disguarded
    FOREIGN KEY (brokerId) REFERENCES User(id),
    FOREIGN KEY (tradeId) REFERENCES Trade(id)
);

CREATE TABLE `Order` (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    brokerId INT UNSIGNED,
    tokenId INT UNSIGNED,
    signature VARCHAR(300),
    amount INT,
    state INT UNSIGNED DEFAULT 0, -- 0 == created, 1 == complete
    executionDate DATE,
    salt INT UNSIGNED,
    hash VARCHAR(200),
    FOREIGN KEY (brokerId) REFERENCES User(id),
    FOREIGN KEY (tokenId) REFERENCES Token(id)
);

CREATE TABLE OrderHolding (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    securityId INT UNSIGNED,
    orderId INT UNSIGNED,
    amount INT,
    cost INT,
    FOREIGN KEY (orderId) REFERENCES `Order`(id),
    FOREIGN KEY (securityId) REFERENCES Security(id)
);

CREATE TABLE OrderTrade (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    orderId INT UNSIGNED,
    tradeId INT UNSIGNED,
    FOREIGN KEY (orderId) REFERENCES `Order`(id),
    FOREIGN KEY (tradeId) REFERENCES Trade(id)
);