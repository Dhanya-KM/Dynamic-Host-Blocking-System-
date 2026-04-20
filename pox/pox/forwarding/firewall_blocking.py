import logging
from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

class LearningFirewall(object):
    def __init__(self, target_host):
        self.target = str(target_host).lower()
        self.mac_to_port = {}  # MAC Learning Table
        core.openflow.addListeners(self)
        print(f"\n[SYSTEM] Learning Firewall Active. Target: {self.target}\n")

    def _handle_PacketIn(self, event):
        packet = event.parse()
        src_mac = str(packet.src).lower()
        dst_mac = str(packet.dst).lower()
        in_port = event.port

        # 1. Update Learning Table
        self.mac_to_port[src_mac] = in_port

        # 2. FIREWALL LOGIC: If source is the target, install a DROP rule
        if src_mac == self.target:
            log.info("FIREWALL: Permanent block for %s", src_mac)
            msg = of.ofp_flow_mod()
            msg.match.dl_src = packet.src
            msg.priority = 65535  # Max Priority
            msg.idle_timeout = 300
            msg.actions.append(of.ofp_action_output(port=of.OFPP_NONE))
            event.connection.send(msg)
            return

        # 3. LEARNING SWITCH LOGIC: If we know where the destination is
        if dst_mac in self.mac_to_port:
            out_port = self.mac_to_port[dst_mac]
            log.info("INSTALLING FLOW: %s -> %s on port %i", src_mac, dst_mac, out_port)
            
            msg = of.ofp_flow_mod()
            msg.match.dl_dst = packet.dst
            msg.match.dl_src = packet.src
            msg.priority = 10  # Normal priority for regular traffic
            msg.actions.append(of.ofp_action_output(port=out_port))
            event.connection.send(msg)

            # Send the current packet out as well
            msg_packet = of.ofp_packet_out()
            msg_packet.data = event.ofp
            msg_packet.actions.append(of.ofp_action_output(port=out_port))
            event.connection.send(msg_packet)
        # Destination unknown, FLOOD it correctly
        else:
            log.info("FLOODING: Unknown destination for %s", dst_mac)
            msg = of.ofp_packet_out()
            msg.data = event.ofp  # Important: Original packet data
            msg.in_port = event.port
            # Directing switch to send out of all ports except the source
            msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            event.connection.send(msg)

def launch():
    print("\n" + "="*30)
    print(" 1: H1 | 2: H2 | 3: H3 ")
    choice = input("Block which host? ").strip()
    mapping = {'1':'00:00:00:00:00:01', '2':'00:00:00:00:00:02', '3':'00:00:00:00:00:03'}
    target = mapping.get(choice, '00:00:00:00:00:01')
    core.registerNew(LearningFirewall, target)
