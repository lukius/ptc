#ifdef HAVE_CONFIG_H
# include "config.h"
#endif

#include <stdio.h>
#include <glib.h>
#include <epan/packet.h>

#include <string.h>

#define PROTO_TAG_PTC "PTC"

#define FIN_FLAG 0x08
#define SYN_FLAG 0x10
#define RST_FLAG 0x20
#define NDT_FLAG 0x40
#define ACK_FLAG 0x80
#define PTC_HEADER_LEN 16

#define FIN_FLAG_MASK 0x01
#define SYN_FLAG_MASK 0x02
#define RST_FLAG_MASK 0x04
#define NDT_FLAG_MASK 0x08
#define ACK_FLAG_MASK 0x10

static int proto_ptc = -1;

static dissector_handle_t data_handle=NULL;

static dissector_handle_t ptc_handle;
static void dissect_ptc(tvbuff_t *tvb, packet_info *pinfo, proto_tree *tree);

static int ptc_proto_num = 202;

static gint hf_ptc_srcport = -1;
static gint hf_ptc_dstport = -1;
static gint hf_ptc_syn_flag = -1;
static gint hf_ptc_fin_flag = -1;
static gint hf_ptc_ack_flag = -1;
static gint hf_ptc_rst_flag = -1;
static gint hf_ptc_ndt_flag = -1;
static gint hf_ptc_seq = -1;
static gint hf_ptc_ack = -1;
static gint hf_ptc_window = -1;

static gint ett_ptc = -1;


void proto_reg_handoff_ptc(void)
{
	static gboolean initialized=FALSE;

	if (!initialized) {
		ptc_handle = create_dissector_handle(dissect_ptc, proto_ptc);
		dissector_add_uint("ip.proto", ptc_proto_num, ptc_handle);
	}

}

void proto_register_ptc (void)
{
	static hf_register_info hf[] =
	{
		{ &hf_ptc_srcport,
		{ "Src Port", "ptc.srcport", FT_UINT16, BASE_DEC, NULL, 0x0, NULL, HFILL }},
        
		{ &hf_ptc_dstport,
		{ "Dst Port", "ptc.dstport", FT_UINT16, BASE_DEC, NULL, 0x0, NULL, HFILL }},
        
        	{ &hf_ptc_fin_flag,
        	{ "FIN", "ptc.flags.fin", FT_BOOLEAN, 8, NULL, FIN_FLAG,  NULL, HFILL }},
        
        	{ &hf_ptc_syn_flag,
        	{ "SYN", "ptc.flags.syn", FT_BOOLEAN, 8, NULL, SYN_FLAG,  NULL, HFILL }},
        
        	{ &hf_ptc_ack_flag,
        	{ "ACK", "ptc.flags.ack", FT_BOOLEAN, 8, NULL, ACK_FLAG,  NULL, HFILL }},
        
        	{ &hf_ptc_rst_flag,
        	{ "RST", "ptc.flags.rst", FT_BOOLEAN, 8, NULL, RST_FLAG,  NULL, HFILL }},
        
        	{ &hf_ptc_ndt_flag,
        	{ "NDT", "ptc.flags.ndt", FT_BOOLEAN, 8, NULL, NDT_FLAG,  NULL, HFILL }},        
        
		{ &hf_ptc_seq,
		{ "SEQ Number", "ptc.seq", FT_UINT32, BASE_DEC, NULL, 0x0, NULL, HFILL }},
		
        	{ &hf_ptc_ack,
        	{ "ACK Number", "ptc.ack", FT_UINT32, BASE_DEC, NULL, 0x0, NULL, HFILL }},

		{ &hf_ptc_window,
		{ "Window", "ptc.window", FT_UINT16, BASE_DEC, NULL, 0x0, NULL, HFILL }},
	};

	static gint *ett[] =
	{
        	&ett_ptc
	};
    
	proto_ptc = proto_register_protocol ("PTC Protocol", "PTC", "ptc");
	proto_register_field_array (proto_ptc, hf, array_length (hf));
	proto_register_subtree_array (ett, array_length (ett));
	register_dissector("ptc", dissect_ptc, proto_ptc);
}
	

static void
dissect_ptc(tvbuff_t *tvb, packet_info *pinfo, proto_tree *tree)
{

	gint offset = 0;
	guint16 iflags, srcport, dstport, window;
	guint32 seq, ack;
	char flags[20] = "";

	if(check_col(pinfo->cinfo, COL_PROTOCOL))
		col_set_str(pinfo->cinfo, COL_PROTOCOL, PROTO_TAG_PTC);
	if(check_col(pinfo->cinfo,COL_INFO))
		col_clear(pinfo->cinfo,COL_INFO);

	srcport = tvb_get_ntohs(tvb, 0);
	dstport = tvb_get_ntohs(tvb, 2);
	seq = tvb_get_ntohl(tvb, 4);
	ack = tvb_get_ntohl(tvb, 8);
	window = tvb_get_ntohs(tvb, 14);
	iflags = tvb_get_ntohs(tvb, 12);

	if( iflags & SYN_FLAG_MASK )
		strcpy(flags, "SYN");
    	if( iflags & ACK_FLAG_MASK )
    	{
		if( strlen(flags) > 0 )
                	strcat(flags, ",ACK");
		else
			strcpy(flags, "ACK");
    	}
    	if( iflags & RST_FLAG_MASK )
    	{
                if( strlen(flags) > 0 )
                        strcat(flags, ",RST");
                else
                        strcpy(flags, "RST");
    	}
    	if( iflags & FIN_FLAG_MASK )
    	{
                if( strlen(flags) > 0 )
                        strcat(flags, ",FIN");
                else
                        strcpy(flags, "FIN");
    	}
    	if( iflags & NDT_FLAG_MASK )
    	{
                if( strlen(flags) > 0 )
                        strcat(flags, ",NDT");
                else
                        strcpy(flags, "NDT");
    	}


	if(check_col(pinfo->cinfo, COL_INFO))
	{
		col_add_fstr(pinfo->cinfo, COL_INFO, "%d > %d [%s] [#SEQ: %d, #ACK: %d, WND: %d]",
		srcport, dstport, flags, seq, ack, window);
	}

	if(tree) 
    	{
		proto_item *ti = NULL;
		proto_tree *ptc_tree = NULL;
        
		ti = proto_tree_add_item(tree, proto_ptc, tvb, 0, PTC_HEADER_LEN, ENC_NA);
		ptc_tree = proto_item_add_subtree(ti, ett_ptc);
        
		proto_tree_add_item(ptc_tree, hf_ptc_srcport, tvb, offset, 2, ENC_BIG_ENDIAN);
		offset += 2;
        
		proto_tree_add_item(ptc_tree, hf_ptc_dstport, tvb, offset, 2, ENC_BIG_ENDIAN);
		offset += 2;
       
		proto_tree_add_item(ptc_tree, hf_ptc_seq, tvb, offset, 4, ENC_BIG_ENDIAN);
		offset += 4;
 
		proto_tree_add_item(ptc_tree, hf_ptc_ack, tvb, offset, 4, ENC_BIG_ENDIAN);
		offset += 4;

		proto_tree_add_item(ptc_tree, hf_ptc_ack_flag, tvb, offset, 1, ENC_BIG_ENDIAN);
		proto_tree_add_item(ptc_tree, hf_ptc_ndt_flag, tvb, offset, 1, ENC_BIG_ENDIAN);
		proto_tree_add_item(ptc_tree, hf_ptc_rst_flag, tvb, offset, 1, ENC_BIG_ENDIAN);
		proto_tree_add_item(ptc_tree, hf_ptc_syn_flag, tvb, offset, 1, ENC_BIG_ENDIAN);
		proto_tree_add_item(ptc_tree, hf_ptc_fin_flag, tvb, offset, 1, ENC_BIG_ENDIAN);
		offset += 2;
        
	        proto_tree_add_item(ptc_tree, hf_ptc_window, tvb, offset, 2, ENC_BIG_ENDIAN);
	}
}	
