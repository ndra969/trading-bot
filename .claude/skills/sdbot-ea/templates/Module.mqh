//+------------------------------------------------------------------+
//| <Layer>/<Name>.mqh — <one line: what this module is responsible for>
//+------------------------------------------------------------------+
#ifndef SDB_<LAYER>_<NAME>_MQH
#define SDB_<LAYER>_<NAME>_MQH

// Only include the same or lower layers (see RULES "Lapisan dan aturan dependensi").
#include <SDBot/Core/Types.mqh>
#include <SDBot/Core/Constants.mqh>
#include <SDBot/Core/Utils.mqh>

//--- Pure helpers (no terminal calls) live as free functions so the unit-test
//--- script can call them without a market. Example:
// double CalcSomething(const double a, const double b) { ... }

class C<Name>
  {
private:
   // m_camelCase members; objects created with new are deleted in the destructor
   bool              m_initialized;

public:
                     C<Name>(void) : m_initialized(false) {}
                    ~C<Name>(void) {}

   // Called from OnInit. Returns false on failure so OnInit can return INIT_FAILED.
   bool              Init(void)
     {
      m_initialized = true;
      return(true);
     }
  };

#endif // SDB_<LAYER>_<NAME>_MQH
