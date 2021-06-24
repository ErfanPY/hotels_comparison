-- --------------------------------------------------------
-- Host:                         192.168.0.240
-- Server version:               8.0.11 - MySQL Community Server - GPL
-- Server OS:                    Linux
-- HeidiSQL Version:             10.3.0.5771
-- --------------------------------------------------------
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */
;

/*!40101 SET NAMES utf8 */
;

/*!50503 SET NAMES utf8mb4 */
;

/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */
;

/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */
;

-- Dumping database structure for Alibaba
DROP DATABASE IF EXISTS `Alibaba`;

CREATE DATABASE IF NOT EXISTS `Alibaba`
/*!40100 DEFAULT CHARACTER SET utf8 */
;

USE `Alibaba`;

-- Dumping structure for table Alibaba.tblAvailabilityInfo
DROP TABLE IF EXISTS `tblAvailabilityInfo`;

CREATE TABLE IF NOT EXISTS `tblAvailabilityInfo` (
  `avl_romID` int(11) unsigned DEFAULT NULL,
  `avlDate` date DEFAULT NULL,
  `avlInsertionDate` date DEFAULT NULL,
  `avlBasePrice` INT UNSIGNED NOT NULL DEFAULT '0',
  `avlDiscountPrice` INT UNSIGNED NOT NULL DEFAULT '0',
  CONSTRAINT `FK_tblAvailabilityInfo_tblRooms` FOREIGN KEY (`avl_romID`) REFERENCES `tblRooms` (`romid`) ON DELETE CASCADE ON UPDATE CASCADE,
  UNIQUE INDEX avl_romID_avlDate_avlInsertionDate (avl_romID, avlDate, avlInsertionDate)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Data exporting was unselected.
-- Dumping structure for table Alibaba.tblHotels
DROP TABLE IF EXISTS `tblHotels`;

CREATE TABLE IF NOT EXISTS `tblHotels` (
  `htlID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `htlEnName` varchar(100) NOT NULL,
  `htlFaName` varchar(100) NOT NULL,
  `htlUUID` varchar(20) DEFAULT NULL,
  `htlCountry` char(2) NOT NULL DEFAULT 'IR',
  `htlCity` VARCHAR(100) NOT NULL DEFAULT '',
  `htlFrom` char(50) NOT NULL DEFAULT '' COMMENT 'A: Alibaba, S: Snapptrip',
  `htlUrl` VARCHAR(512),
  PRIMARY KEY (`htlID`),
  KEY `htlEnName` (`htlEnName`),
  KEY `htlFaName` (`htlFaName`),
  KEY `htlFrom` (`htlFrom`),
  KEY `htlIdentifier` (`htlUUID`),
  UNIQUE INDEX htlEnName_htlFaName_htlCity_htlFrom (htlEnName, htlFaName, htlCity, htlFrom)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Data exporting was unselected.
-- Dumping structure for table Alibaba.tblRooms
DROP TABLE IF EXISTS `tblRooms`;

CREATE TABLE IF NOT EXISTS `tblRooms` (
  `romID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `rom_htlID` int(11) unsigned DEFAULT NULL,
  `romName` varchar(100) DEFAULT NULL,
  `romType` char(1) DEFAULT NULL COMMENT 'S: Sinbgle, D: Double, T: Triple, Q: Quad, U: Queen, K: King, T: Tween, 2: Double Double, M: Master ',
  `romUUID` varchar(100) DEFAULT NULL,
  `romAdditives` json DEFAULT NULL,
  PRIMARY KEY (`romID`),
  KEY `romUUID` (`romUUID`),
  KEY `FK_tblRooms_tblHotels` (`rom_htlID`),
  CONSTRAINT `FK_tblRooms_tblHotels` FOREIGN KEY (`rom_htlID`) REFERENCES `tblHotels` (`htlID`) ON DELETE CASCADE ON UPDATE CASCADE,
  UNIQUE INDEX rom_htlID_romName_romType (rom_htlID, romName, romType)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Data exporting was unselected.
-- Dumping structure for table Alibaba.tblTokens
DROP TABLE IF EXISTS `tblTokens`;

CREATE TABLE IF NOT EXISTS `tblTokens` (
  `tokID` int(11) NOT NULL AUTO_INCREMENT,
  `tokUUID` varchar(100) DEFAULT NULL,
  `tokCreationDate` datetime DEFAULT CURRENT_TIMESTAMP,
  `tokLastAccessDate` datetime DEFAULT NULL,
  `tokSatatus` char(1) NOT NULL DEFAULT 'A' COMMENT 'A: Active, R: Removed, B: Banned',
  PRIMARY KEY (`tokID`),
  UNIQUE KEY `tokUUID` (`tokUUID`),
  KEY `tokCreationDate` (`tokCreationDate`),
  KEY `tokSatatus` (`tokSatatus`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Data exporting was unselected.
CREATE TABLE tblAlert (
  alrID INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  alrDateTime DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  alrRoomUUID VARCHAR(100) NOT NULL COLLATE 'utf8mb4_unicode_ci',
  alrOnDate DATE NULL DEFAULT NULL,
  alrType CHAR(50) NOT NULL COMMENT 'P: Price, D: Discount, R: Reserve' COLLATE 'utf8mb4_unicode_ci',
  alrA_romID INT(11) UNSIGNED NOT NULL,
  alrS_romID INT(11) UNSIGNED NOT NULL,
  alrInfo LONGTEXT NOT NULL COLLATE 'utf8mb4_bin',
  alrStatus CHAR(50) NOT NULL DEFAULT 'N' COMMENT 'N: New, R: Reported' COLLATE 'utf8mb4_unicode_ci',
  PRIMARY KEY (alrID),
  INDEX alrType (alrType),
  INDEX alrOnDate (alrOnDate),
  INDEX alrRoomUUID (alrRoomUUID),
  INDEX alrDateTime (alrDateTime),
  INDEX alrStatus (alrStatus),
  INDEX FK_tblAlert_tblRooms (alrA_romID),
  INDEX FK_tblAlert_tblRooms_2 (alrS_romID),
  CONSTRAINT FK_tblAlert_tblRooms FOREIGN KEY (alrA_romID) REFERENCES tblRooms (romid) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT FK_tblAlert_tblRooms_2 FOREIGN KEY (alrS_romID) REFERENCES tblRooms (romid) ON UPDATE CASCADE ON DELETE CASCADE
) COLLATE = 'utf8mb4_unicode_ci' ENGINE = InnoDB AUTO_INCREMENT = 261;

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */
;

/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */
;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */
;