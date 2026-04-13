from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

class FirewallBlocking (object):
  def __init__ (self):
    core.openflow.addListeners(self)

  def _handle_PacketIn (self, event):
    packet = event.parse()
    
    # Blocking Host 3 (MAC: 00:00:00:00:00:03)
    if packet.src == '00:00:00:00:00:03':
      log.info("Intruder Detected! Blocking Host 3: %s", packet.src)
      
      msg = of.ofp_flow_mod()
      msg.priority = 100 # High priority rule
      msg.match.dl_src = packet.src
      
      # Setting long timeouts so flow table doesn't clear immediately
      msg.idle_timeout = 600 
      msg.hard_timeout = 600
      
      # Action: NONE (Drop)
      msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))
      event.connection.send(msg)
      
      log.info("FLOW TABLE UPDATED: Drop rule installed for 10 minutes.")
      return

    # Normal forwarding for other hosts
    msg = of.ofp_packet_out()
    msg.data = event.ofp
    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
    event.connection.send(msg)

def launch ():
  core.registerNew(FirewallBlocking)
