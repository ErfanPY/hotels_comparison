-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               10.5.8-MariaDB - MariaDB package
-- Server OS:                    Linux
-- HeidiSQL Version:             11.3.0.6295
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Dumping database structure for Alibaba
DROP DATABASE IF EXISTS `Alibaba`;
CREATE DATABASE IF NOT EXISTS `Alibaba` /*!40100 DEFAULT CHARACTER SET utf8 */;
USE `Alibaba`;

-- Dumping structure for table Alibaba.tblAlert
DROP TABLE IF EXISTS `tblAlert`;
CREATE TABLE IF NOT EXISTS `tblAlert` (
  `alrID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `alrDateTime` datetime DEFAULT current_timestamp(),
  `alrRoomUUID` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `alrOnDate` date DEFAULT NULL,
  `alrType` char(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'P: Price, D: Discount, R: Reserve, M: MealPlan',
  `alrA_romID` int(11) unsigned NOT NULL,
  `alrS_romID` int(11) unsigned NOT NULL,
  `alrInfo` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `alrStatus` char(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'N' COMMENT 'N: New, R: Reported',
  PRIMARY KEY (`alrID`),
  KEY `alrType` (`alrType`),
  KEY `alrOnDate` (`alrOnDate`),
  KEY `alrRoomUUID` (`alrRoomUUID`),
  KEY `alrDateTime` (`alrDateTime`),
  KEY `alrStatus` (`alrStatus`),
  KEY `FK_tblAlert_tblRooms` (`alrA_romID`),
  KEY `FK_tblAlert_tblRooms_2` (`alrS_romID`),
  CONSTRAINT `FK_tblAlert_tblRooms` FOREIGN KEY (`alrA_romID`) REFERENCES `tblRooms` (`romID`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_tblAlert_tblRooms_2` FOREIGN KEY (`alrS_romID`) REFERENCES `tblRooms` (`romID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=331 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Data exporting was unselected.

-- Dumping structure for table Alibaba.tblAvailabilityInfo
DROP TABLE IF EXISTS `tblAvailabilityInfo`;
CREATE TABLE IF NOT EXISTS `tblAvailabilityInfo` (
  `avl_romID` int(11) unsigned DEFAULT NULL,
  `avlDate` date DEFAULT NULL,
  `avlInsertionDate` date DEFAULT NULL,
  `avlBasePrice` int(10) unsigned NOT NULL DEFAULT 0,
  `avlDiscountPrice` int(10) unsigned NOT NULL DEFAULT 0,
  UNIQUE KEY `avl_romID_avlDate_avlInsertionDate` (`avl_romID`,`avlDate`,`avlInsertionDate`),
  CONSTRAINT `FK_tblAvailabilityInfo_tblRooms` FOREIGN KEY (`avl_romID`) REFERENCES `tblRooms` (`romid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Data exporting was unselected.

-- Dumping structure for table Alibaba.tblHotels
DROP TABLE IF EXISTS `tblHotels`;
CREATE TABLE IF NOT EXISTS `tblHotels` (
  `htlID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `htlEnName` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `htlFaName` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `htlUUID` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `htlCountry` char(2) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'IR',
  `htlCity` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `htlFrom` char(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT 'A: Alibaba, S: Snapptrip',
  `htlUrl` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`htlID`),
  UNIQUE KEY `htlEnName_htlFaName_htlCity_htlFrom` (`htlEnName`,`htlFaName`,`htlCity`,`htlFrom`),
  KEY `htlEnName` (`htlEnName`),
  KEY `htlFaName` (`htlFaName`),
  KEY `htlFrom` (`htlFrom`),
  KEY `htlIdentifier` (`htlUUID`)
) ENGINE=InnoDB AUTO_INCREMENT=3422 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Data exporting was unselected.

-- Dumping structure for table Alibaba.tblRooms
DROP TABLE IF EXISTS `tblRooms`;
CREATE TABLE IF NOT EXISTS `tblRooms` (
  `romID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `rom_htlID` int(11) unsigned DEFAULT NULL,
  `romName` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `romType` char(1) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'S: Sinbgle, D: Double, T: Triple, Q: Quad, U: Queen, K: King, T: Tween, 2: Double Double, M: Master ',
  `romUUID` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `romAdditives` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `romMealPlan` char(3) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'RO: Room only, BB: Bed with breakfast',
  PRIMARY KEY (`romID`),
  UNIQUE KEY `rom_htlID_romName_romType` (`rom_htlID`,`romName`,`romType`),
  KEY `romUUID` (`romUUID`),
  KEY `FK_tblRooms_tblHotels` (`rom_htlID`),
  CONSTRAINT `FK_tblRooms_tblHotels` FOREIGN KEY (`rom_htlID`) REFERENCES `tblHotels` (`htlID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=19536 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Data exporting was unselected.

-- Dumping structure for table Alibaba.tblRoomsOpinions
DROP TABLE IF EXISTS `tblRoomsOpinions`;
CREATE TABLE IF NOT EXISTS `tblRoomsOpinions` (
  `rop_romID` int(10) unsigned NOT NULL,
  `ropUserName` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `ropDate` datetime NOT NULL,
  `ropScrapDate` datetime NOT NULL DEFAULT current_timestamp(),
  `ropStrengths` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `ropWeakness` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `ropText` text COLLATE utf8mb4_unicode_ci NOT NULL,
  KEY `FK__tblRooms` (`rop_romID`),
  CONSTRAINT `FK__tblRooms` FOREIGN KEY (`rop_romID`) REFERENCES `tblRooms` (`romID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Data exporting was unselected.

-- Dumping structure for table Alibaba.tblTokens
DROP TABLE IF EXISTS `tblTokens`;
CREATE TABLE IF NOT EXISTS `tblTokens` (
  `tokID` int(11) NOT NULL AUTO_INCREMENT,
  `tokUUID` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tokCreationDate` datetime DEFAULT current_timestamp(),
  `tokLastAccessDate` datetime DEFAULT NULL,
  `tokSatatus` char(1) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'A' COMMENT 'A: Active, R: Removed, B: Banned',
  PRIMARY KEY (`tokID`),
  UNIQUE KEY `tokUUID` (`tokUUID`),
  KEY `tokCreationDate` (`tokCreationDate`),
  KEY `tokSatatus` (`tokSatatus`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Data exporting was unselected.

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
