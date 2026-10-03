//+------------------------------------------------------------------+
//| TestCodec.mqh — waktu UTC, JSON kanonik, dan hash input untuk tabel
//| sessions dan kolom waktu (spec 03 Req 7.3, 8.5).
//+------------------------------------------------------------------+
#ifndef SDB_SUITES_TESTCODEC_MQH
#define SDB_SUITES_TESTCODEC_MQH

#include <SDBotTests/TestFramework.mqh>
#include <SDBot/Core/Inputs.mqh>
#include <SDBot/Core/Utils.mqh>

void RunTestCodec()
  {
   TfBeginSuite("Codec");

   AssertIntEq("TC-SU-01a", "selisih server-GMT 10795 detik dibulatkan ke +3 jam", RoundUtcOffset(10795), 10800);
   AssertIntEq("TC-SU-01b", "selisih -18010 dibulatkan ke -5 jam", RoundUtcOffset(-18010), -18000);
   AssertIntEq("TC-SU-01c", "selisih 1810 dibulatkan ke 30 menit", RoundUtcOffset(1810), 1800);
   AssertIntEq("TC-SU-01d", "selisih 0 tetap 0 (tester)", RoundUtcOffset(0), 0);
   datetime server = D'2026.09.29 13:00:00';
   AssertIntEq("TC-DB-11", "ServerToUtc dengan offset +3 jam", (long)ServerToUtc(server, 10800), (long)D'2026.09.29 10:00:00');

   string k1[] = {"b", "a", "c"};
   string v1[] = {"2", "\"x\"", "true"};
   AssertStrEq("TC-SU-02a", "CanonicalJson mengurutkan kunci", CanonicalJson(k1, v1), "{\"a\":\"x\",\"b\":2,\"c\":true}");
   AssertStrEq("TC-SU-02b", "JsonStr meng-escape kutip, backslash, dan baris baru",
               JsonStr("a\"b\\c\nd"), "\"a\\\"b\\\\c\\nd\"");
   string k4[] = {"a", "Da", "B", "DD"};
   string v4[] = {"1", "2", "3", "4"};
   AssertStrEq("TC-SU-02d", "CanonicalJson urut ordinal peka huruf besar (sama dengan json.dumps sort_keys Python)",
               CanonicalJson(k4, v4), "{\"B\":3,\"DD\":4,\"Da\":2,\"a\":1}");
   AssertStrEq("TC-SU-02c", "JsonNum tanpa nol berlebih", JsonNum(0.5) + "," + JsonNum(15.0) + "," + JsonNum(2026091901), "0.5,15,2026091901");

   AssertStrEq("TC-SU-03", "Sha256Hex(\"abc\") sesuai vektor uji NIST", Sha256Hex("abc"),
               "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");

   string k2[] = {"c", "a", "b"};
   string v2[] = {"true", "\"x\"", "2"};
   AssertStrEq("TC-DB-14a", "hash sama untuk input sama dengan urutan berbeda",
               Sha256Hex(CanonicalJson(k1, v1)), Sha256Hex(CanonicalJson(k2, v2)));
   v2[2] = "3";
   AssertTrue("TC-DB-14b", "hash berbeda bila satu nilai berbeda",
              Sha256Hex(CanonicalJson(k1, v1)) != Sha256Hex(CanonicalJson(k2, v2)));

   string json = CurrentInputsJson();
   AssertTrue("TC-SU-04a", "JSON input berisi nilai default risk per trade", StringFind(json, "\"InpRiskPerTradePct\":0.5") >= 0);
   AssertTrue("TC-SU-04b", "JSON input dimulai kunci pertama urutan abjad",
              StringFind(json, "{\"InpAllowLiveTrading\":") == 0);
   int keys = 0;
   for(int i = 0; i < StringLen(json); i++)
      if(StringGetCharacter(json, i) == ':')
         keys++;
   AssertIntEq("TC-SU-04c", "JSON input berisi 38 input (28 + 5 zona spec 11 + 5 sinyal spec 13)", keys, 38);
   AssertTrue("TC-SU-04d", "JSON input tanpa token dan chat ID (spec 09 Req 1.3)",
              StringFind(json, "InpTelegramToken") < 0 && StringFind(json, "InpTelegramChatID") < 0 &&
              StringFind(json, "\"InpTelegramConfigured\":false") >= 0 && StringFind(json, "\"InpHeartbeatMinutes\":60") >= 0);

   TfEndSuite();
  }

#endif // SDB_SUITES_TESTCODEC_MQH
