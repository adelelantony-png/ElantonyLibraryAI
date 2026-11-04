# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Google Drive Ecclesiastical Repository Harvester (Phase 7 Integration)
Catalogs, verifies, and synchronizes foundational Google Drive church libraries:
- Fr. Tadros Yacoub Malaty Complete Works (Tafseer & Patristics)
- Pope Shenouda III Papal Library
- Holy Synod Servant Curricula
- Church History & Biblical Commentaries
- Fr. Bishoy Kamel Complete Works
"""

from typing import List, Dict, Any
from pathlib import Path
from elantony.core.config import settings
from elantony.core.logging import logger


GDRIVE_LIBRARIES_CATALOG = [
    {
        "id": "tadros_malaty_complete",
        "name": "جميع أعمال القمص تادرس يعقوب ملطي",
        "folder_id": "1N_4em3z-URYgjegQ-G49N9xonhW_Lnpm",
        "url": "https://drive.google.com/drive/folders/1N_4em3z-URYgjegQ-G49N9xonhW_Lnpm",
        "category": "تفسير الكتاب المقدس والآبائيات الجامعة",
        "tier": 1,
        "importance": "موسوعة تفسيرية وآبائية شاملة للعهدين القديم والجديد"
    },
    {
        "id": "pope_shenouda_complete",
        "name": "مكتبة قداسة البابا شنودة الثالث الكاملة",
        "folder_id": "0B9W2QsO5NzBWb0NYMzZseWh1c1k",
        "url": "https://drive.google.com/drive/folders/0B9W2QsO5NzBWb0NYMzZseWh1c1k?resourcekey=0-9SQuJi1sqFA13zipZdsSlA",
        "category": "لاهوت دفاعي ورعويات وروحيات",
        "tier": 1,
        "importance": "أكثر من 130 كتاباً تشكل العمود الفقري للتعليم القبطي المعاصر"
    },
    {
        "id": "holy_synod_servants",
        "name": "سلسلة دراسات للخدام - المجمع المقدس",
        "folder_id": "1ZxhhRZy-pG-C8kUHhpPNWUPfwwR8vCxr",
        "url": "https://drive.google.com/drive/folders/1ZxhhRZy-pG-C8kUHhpPNWUPfwwR8vCxr",
        "category": "مناهج إعداد خدام وعقيدة أرثوذكسية",
        "tier": 1,
        "importance": "المنهج التعليمي الرسمي الصادر عن لجان المجمع المقدس"
    },
    {
        "id": "church_history_synod",
        "name": "تاريخ الكنيسة القبطية الأرثوذكسية",
        "folder_id": "0B9W2QsO5NzBWNFpkcm45STYwZmc",
        "url": "https://drive.google.com/drive/folders/0B9W2QsO5NzBWNFpkcm45STYwZmc?resourcekey=0-E7ru1VMzIM4hKh1elKYc7g",
        "category": "تاريخ كنسي وسنكسار ومجامع",
        "tier": 2,
        "importance": "سير الآباء والشهداء وتاريخ البطاركة والمجامع المسكونية"
    },
    {
        "id": "bible_commentaries",
        "name": "تفسير أسفار الكتاب المقدس",
        "folder_id": "0B9W2QsO5NzBWSFItWHJBY2pxN2s",
        "url": "https://drive.google.com/drive/folders/0B9W2QsO5NzBWSFItWHJBY2pxN2s?resourcekey=0-qllAYOYMPPB_tJd0sGJp-Q",
        "category": "تفاسير العهدين",
        "tier": 1,
        "importance": "دراسات لغوية ولاهوتية وشروح تفصيلية للأسفار"
    },
    {
        "id": "fr_bishoy_kamel",
        "name": "كل ما يخص القمص بيشوي كامل",
        "folder_id": "1Lq4GbfYj4K_2eTuqMZZMReU6R66dQsad",
        "url": "https://drive.google.com/drive/folders/1Lq4GbfYj4K_2eTuqMZZMReU6R66dQsad",
        "category": "روحيات ورعويات ولاهوت الصليب",
        "tier": 2,
        "importance": "كتابات وتأملات رائدة في الخدمة والبذل ولاهوت الكنيسة المعاش"
    },
    {
        "id": "khedma_library_drive",
        "name": "مكتبة الخادم الشاملة",
        "folder_id": "1C4mMKVMJ1uBXlFdbNufdS__uclpZUEB7",
        "url": "https://drive.google.com/drive/folders/1C4mMKVMJ1uBXlFdbNufdS__uclpZUEB7",
        "category": "موسوعات ومراجع للخدام",
        "tier": 2,
        "importance": "أبحاث وعروض ووسائل تعليمية ومراجع مساندة"
    }
]


class GDriveHarvesterService:
    """Manages Drive libraries metadata, download triggers, and ingestion pipeline."""

    def __init__(self):
        self.catalog = GDRIVE_LIBRARIES_CATALOG
        self.destination_dir = Path(r"I:\2021\2020\✠ Cross Coptic Library ✠\وارد_جوجل_درايف")
        if not self.destination_dir.parent.exists():
            self.destination_dir = settings.base_dir / "books" / "gdrive_harvest"
        self.destination_dir.mkdir(parents=True, exist_ok=True)

    def list_libraries(self) -> List[Dict[str, Any]]:
        """Returns the complete Drive catalog."""
        return self.catalog

    def get_library_by_id(self, lib_id: str) -> Dict[str, Any]:
        """Finds library entry by ID."""
        for lib in self.catalog:
            if lib["id"] == lib_id:
                return lib
        return {}


# Global drive harvester service
gdrive_harvester = GDriveHarvesterService()
